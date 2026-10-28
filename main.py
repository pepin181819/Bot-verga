import sys
try:
    import audioop
except ModuleNotFoundError:
    try:
        import audioop_lts as audioop
        sys.modules['audioop'] = audioop
    except:
        pass

import os, json, discord, asyncio, time, shutil, traceback
from discord.ext import commands, tasks
from datetime import datetime, timezone
from collections import defaultdict
from dotenv import load_dotenv
from flask import Flask
from threading import Thread

load_dotenv()
TOKEN = os.getenv("DISCORD_BOT_TOKEN") or os.getenv("TOKEN") or os.getenv("DISCORD_TOKEN")
MY_ID = 1310357536087740450

app = Flask(__name__)
@app.route('/')
def home(): return "ANTINUKE ON"
def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port, threaded=True, use_reloader=False)
Thread(target=run_flask, daemon=True).start()
time.sleep(2)

OWNER_FILE="owners.json"
WHITELIST_PINGS_FILE="whitelist_pings.json"
WHITELIST_ROLES_FILE="whitelist_roles.json"
ROLE_IMMUNE_FILE="role_immune.json"
VOICE_FILE="voice.json"
BOTS_FILE="bots_whitelist.json"
VC_IMMUNE_FILE="vc_inmunes.json"
BACKUP_DIR="backups"
MUSICA_DIR="musica"
os.makedirs(BACKUP_DIR, exist_ok=True)
os.makedirs(MUSICA_DIR, exist_ok=True)

USOS = {
    "r_add": "Uso: _r_add @usuario nombre_rol", "r_remove": "Uso: _r_remove @usuario nombre_rol",
    "whitelist_add": "Uso: _whitelist_add r/p ID", "whitelist_remove": "Uso: _whitelist_remove r/p ID",
    "whitelist_list": "Uso: _whitelist_list", "role_inmune_add": "Uso: _role_inmune_add nombre_rol",
    "role_inmune_remove": "Uso: _role_inmune_remove nombre_rol", "role_inmune_list": "Uso: _role_inmune_list",
    "vc_inmune_add": "Uso: _vc_inmune_add #canal", "vc_inmune_remove": "Uso: _vc_inmune_remove #canal",
    "vc_inmune_list": "Uso: _vc_inmune_list", "mibebe": "Uso: _mibebe ID", "b_add": "Uso: _b_add ID",
    "b_remove": "Uso: _b_remove ID", "b_list": "Uso: _b_list", "owner_add": "Uso: _owner_add ID",
    "owner_remove": "Uso: _owner_remove ID", "owner_list": "Uso: _owner_list", "backup": "Uso: _backup create/load",
    "userinfo": "Uso: _userinfo @usuario", "serverinfo": "Uso: _serverinfo", "ban": "Uso: _ban ID motivo",
    "unban": "Uso: _unban ID", "kick": "Uso: _kick ID", "purge": "Uso: _purge cantidad",
    "lock": "Uso: _lock", "unlock": "Uso: _unlock", "say": "Uso: _say texto", "nick": "Uso: _nick ID nick",
    "quitar": "Uso: _quitar nombre",
}
MUSICA_EXCLUIR = ["join","leave","tuputamadre","stop","guardar","list","quitar"]

def load_guild_map(path):
    if os.path.exists(path):
        try:
            with open(path,"r") as f:
                raw=json.load(f)
            if isinstance(raw, dict): return {str(k): set(map(int, v)) for k,v in raw.items()}
        except: return {}
    return {}
def save_guild_map(path, data):
    out = {str(k): list(v) for k,v in data.items()}
    with open(path,"w") as f: json.dump(out,f)
def load_json_file(path):
    if os.path.exists(path):
        try:
            with open(path,"r") as f: return json.load(f)
        except: return {}
    return {}
def save_json_file(path, data):
    with open(path,"w") as f: json.dump(data,f)

OWNER_MAP = load_guild_map(OWNER_FILE)
WHITELIST_PINGS_MAP = load_guild_map(WHITELIST_PINGS_FILE)
WHITELIST_ROLES_MAP = load_guild_map(WHITELIST_ROLES_FILE)
IMMUNE_ROLES_MAP = load_guild_map(ROLE_IMMUNE_FILE)
BOTS_MAP = load_guild_map(BOTS_FILE)
VOICE_CHANNELS = load_json_file(VOICE_FILE)

intents=discord.Intents.default()
intents.message_content=True
intents.members=True
intents.guilds=True
intents.presences=True
intents.voice_states=True
bot=commands.Bot(command_prefix="_",intents=intents,help_command=None)

voice_clients={}
guardar_sessions={}
pending_audio=set()
immune_members_cache={}

def embed_chido(text): return discord.Embed(description=text, color=0x0b0b0b)
async def send_uso(ctx):
    name = ctx.command.name if ctx.command else ""
    if name in USOS: await ctx.send(embed=embed_chido(USOS[name]))
def extract_id(text):
    nums = ''.join(filter(str.isdigit, str(text)))
    return int(nums) if nums else None
def find_role_by_name(guild, name):
    name = name.lower().strip()
    r = discord.utils.find(lambda x: x.name.lower() == name, guild.roles)
    if r: return r
    r = discord.utils.find(lambda x: name in x.name.lower(), guild.roles)
    return r
def get_guild_set(map_data, guild_id): return map_data.get(str(guild_id), set())
def is_main_owner(uid): return uid == MY_ID
def is_owner(guild_id, uid):
    if uid == MY_ID: return True
    return uid in get_guild_set(OWNER_MAP, guild_id)
def has_perm(ctx):
    try:
        if ctx.author.id == MY_ID: return True
        if not ctx.guild: return False
        if ctx.author.id == ctx.guild.owner_id: return True
        return is_owner(ctx.guild.id, ctx.author.id)
    except: return ctx.author.id == MY_ID
def can_use_r_cmd(guild, uid):
    if uid == MY_ID: return True
    try:
        if uid == guild.owner_id: return True
        if uid in get_guild_set(OWNER_MAP, guild.id): return True
        if uid in get_guild_set(WHITELIST_ROLES_MAP, guild.id): return True
    except: pass
    return False
def can_give_manual(guild, uid):
    if uid == MY_ID: return True
    try:
        if uid == guild.owner_id: return True
        if uid in get_guild_set(OWNER_MAP, guild.id): return True
        if uid in get_guild_set(WHITELIST_ROLES_MAP, guild.id): return True
    except: pass
    return False

LIMIT=3; TIME_WINDOW=10; cache=defaultdict(list)
def is_spam(uid):
    now=time.time()
    cache[uid]=[t for t in cache[uid] if now-t < TIME_WINDOW]
    cache[uid].append(now)
    return len(cache[uid])>LIMIT
def has_immune_role(guild, uid):
    try:
        m = guild.get_member(uid)
        if m:
            immune_ids = get_guild_set(IMMUNE_ROLES_MAP, guild.id)
            if any(r.id in immune_ids for r in m.roles): return True
        return uid in immune_members_cache.get(str(guild.id), set())
    except: return False
def is_safe(guild, uid):
    if uid == MY_ID: return True
    if not guild: return uid == MY_ID
    try:
        if uid in get_guild_set(OWNER_MAP, guild.id): return True
        if uid == guild.owner_id: return True
    except: pass
    return False
def is_pings_allowed(guild, uid):
    if is_safe(guild, uid): return True
    if uid in get_guild_set(WHITELIST_PINGS_MAP, guild.id): return True
    return False
def is_links_allowed(guild, uid): return is_safe(guild, uid)

async def auto_backup(guild):
    try:
        path = f"{BACKUP_DIR}/{guild.id}.json"
        data = {"guild_name": guild.name, "roles": [], "categories": [], "channels": []}
        for r in reversed(guild.roles):
            if r.is_default() or r.managed or r.is_bot_managed(): continue
            data["roles"].append({"name": r.name, "color": r.color.value, "permissions": r.permissions.value, "hoist": r.hoist, "mentionable": r.mentionable})
        for cat in guild.categories: data["categories"].append({"name": cat.name, "position": cat.position})
        for ch in guild.channels:
            if isinstance(ch, discord.CategoryChannel): continue
            data["channels"].append({"name": ch.name, "type": str(ch.type), "category": ch.category.name if ch.category else None, "position": ch.position})
        with open(path, "w", encoding="utf-8") as f: json.dump(data, f, indent=4)
        return path
    except: return None

async def nuke_punish(guild, uid, reason):
    if is_safe(guild, uid): return
    if has_immune_role(guild, uid): return
    try: path = await auto_backup(guild)
    except: path = None
    try:
        owners_del_server = get_guild_set(OWNER_MAP, guild.id)
        for owner_id in owners_del_server:
            try:
                u = await bot.fetch_user(owner_id)
                if path: await u.send(f"ANTINUKE {guild.name} {reason} by ( {uid} )", file=discord.File(path))
                else: await u.send(f"ANTINUKE {guild.name} {reason} by ( {uid} )")
            except: pass
    except: pass
    try:
        m=guild.get_member(uid) or await guild.fetch_member(uid)
        await guild.ban(m, reason=f"ANTINUKE {reason}")
    except: pass

async def bloquear_canal_vc(canal):
    try:
        await canal.set_permissions(canal.guild.default_role, manage_channels=False, manage_permissions=False)
        for rol in canal.guild.roles:
            if rol.permissions.manage_channels or rol.permissions.administrator:
                if rol.id != canal.guild.me.top_role.id and not rol.is_default():
                    try: await canal.set_permissions(rol, manage_channels=False, manage_permissions=False)
                    except: pass
    except: pass

@tasks.loop(seconds=30)
async def loop_vc_proteccion():
    data = load_json_file(VC_IMMUNE_FILE)
    for guild in bot.guilds:
        gid = str(guild.id)
        if gid not in data: continue
        for cid in list(data[gid].keys()):
            canal = guild.get_channel(int(cid))
            if canal: await bloquear_canal_vc(canal)

@bot.event
async def on_ready():
    print(f"Listo {bot.user}")
    for guild in bot.guilds:
        gid = str(guild.id)
        immune_ids = get_guild_set(IMMUNE_ROLES_MAP, guild.id)
        immune_members_cache[gid] = set()
        for m in guild.members:
            if any(r.id in immune_ids for r in m.roles):
                immune_members_cache[gid].add(m.id)
        if gid in VOICE_CHANNELS:
            try:
                ch_id = VOICE_CHANNELS[gid]
                channel = guild.get_channel(ch_id) or await bot.fetch_channel(ch_id)
                if isinstance(channel, discord.VoiceChannel):
                    if guild.voice_client:
                        try: await guild.voice_client.disconnect(force=True)
                        except: pass
                    vc = await channel.connect(self_deaf=False, self_mute=False, timeout=20.0, reconnect=True)
                    voice_clients[guild.id] = vc
            except: pass
    try:
        if not loop_vc_proteccion.is_running(): loop_vc_proteccion.start()
    except: pass

@bot.event
async def on_voice_state_update(member, before, after):
    if member.id == bot.user.id and before.channel and not after.channel:
        gid = str(before.channel.guild.id)
        if gid in VOICE_CHANNELS:
            await asyncio.sleep(3)
            try:
                channel = before.channel.guild.get_channel(VOICE_CHANNELS[gid])
                if channel and not before.channel.guild.voice_client:
                    vc = await channel.connect(self_deaf=False, self_mute=False, timeout=20.0, reconnect=True)
                    voice_clients[before.channel.guild.id] = vc
            except: pass

@bot.event
async def on_member_update(before, after):
    added = [r for r in after.roles if r not in before.roles]
    try:
        gid = str(after.guild.id)
        immune_ids = get_guild_set(IMMUNE_ROLES_MAP, after.guild.id)
        has_imm = any(r.id in immune_ids for r in after.roles)
        immune_members_cache.setdefault(gid, set())
        if has_imm: immune_members_cache[gid].add(after.id)
        else: immune_members_cache[gid].discard(after.id)
    except: pass
    if not added or after.bot: return
    try:
        async for entry in after.guild.audit_logs(limit=5, action=discord.AuditLogAction.member_role_update):
            if (datetime.now(timezone.utc)-entry.created_at).total_seconds() > 20: continue
            if entry.target.id!= after.id: continue
            executor = entry.user
            if bot.user and executor.id == bot.user.id: return
            if executor.id == MY_ID: return
            if "r_add" in (entry.reason or "").lower() or "r_remove" in (entry.reason or "").lower(): return
            if can_give_manual(after.guild, executor.id): return
            try: await after.edit(roles=before.roles, reason="Solo Whitelist R")
            except: pass
            return
    except: pass

@bot.event
async def on_member_ban(guild,user):
    try:
        await asyncio.sleep(1)
        async for e in guild.audit_logs(limit=1,action=discord.AuditLogAction.ban):
            if (datetime.now(timezone.utc)-e.created_at).total_seconds()>10: continue
            if e.target.id!= user.id: continue
            if has_immune_role(guild, user.id):
                if is_safe(guild, e.user.id): return
                try:
                    await guild.unban(user, reason="Proteccion inmune")
                    await guild.ban(e.user, reason=f"Intento banear inmune {user.id}")
                except: pass
                return
            if is_safe(guild, e.user.id): return
            if is_spam(e.user.id): await nuke_punish(guild,e.user.id,"Mass Ban")
    except: pass

@bot.event
async def on_member_remove(member):
    try:
        await asyncio.sleep(1)
        async for e in member.guild.audit_logs(limit=1,action=discord.AuditLogAction.kick):
            if (datetime.now(timezone.utc)-e.created_at).total_seconds()>10: continue
            if e.target.id!=member.id: continue
            if has_immune_role(member.guild, member.id):
                if is_safe(member.guild, e.user.id): return
                try: await member.guild.ban(e.user, reason=f"Intento kickear inmune {member.id}")
                except: pass
                return
            if is_safe(member.guild, e.user.id): return
            if is_spam(e.user.id): await nuke_punish(member.guild,e.user.id,"Mass Kick")
    except: pass

@bot.event
async def on_guild_channel_delete(channel):
    try:
        if isinstance(channel, discord.VoiceChannel):
            data = load_json_file(VC_IMMUNE_FILE)
            gid = str(channel.guild.id)
            if gid in data and str(channel.id) in data[gid]:
                info = data[gid][str(channel.id)]
                await asyncio.sleep(0.5)
                async for e in channel.guild.audit_logs(limit=3, action=discord.AuditLogAction.channel_delete):
                    if (datetime.now(timezone.utc)-e.created_at).total_seconds()>10: continue
                    if e.target.id != channel.id: continue
                    if is_safe(channel.guild, e.user.id):
                        data[gid].pop(str(channel.id), None)
                        save_json_file(VC_IMMUNE_FILE, data)
                        return
                    try: await channel.guild.ban(e.user, reason=f"Borro VC inmune {info['name']}")
                    except: pass
                    try:
                        cat = channel.guild.get_channel(info['category']) if info.get('category') else None
                        nuevo = await channel.guild.create_voice_channel(name=info['name'], bitrate=info.get('bitrate', 64000), user_limit=info.get('limit', 0), category=cat, reason="VC Inmune restaurado")
                        data[gid].pop(str(channel.id), None)
                        data[gid][str(nuevo.id)] = info
                        save_json_file(VC_IMMUNE_FILE, data)
                        await bloquear_canal_vc(nuevo)
                    except: pass
                    return
    except: pass
    try:
        async for e in channel.guild.audit_logs(limit=1,action=discord.AuditLogAction.channel_delete):
            if (datetime.now(timezone.utc)-e.created_at).total_seconds()>10: continue
            if is_safe(channel.guild, e.user.id): return
            if is_spam(e.user.id): await nuke_punish(channel.guild,e.user.id,"Channel Delete")
    except: pass

@bot.event
async def on_guild_channel_create(channel):
    try:
        async for e in channel.guild.audit_logs(limit=1,action=discord.AuditLogAction.channel_create):
            if (datetime.now(timezone.utc)-e.created_at).total_seconds()>10: continue
            if is_safe(channel.guild, e.user.id): return
            if is_spam(e.user.id): await nuke_punish(channel.guild,e.user.id,"Channel Create")
    except: pass
@bot.event
async def on_guild_role_delete(role):
    try:
        async for e in role.guild.audit_logs(limit=1,action=discord.AuditLogAction.role_delete):
            if (datetime.now(timezone.utc)-e.created_at).total_seconds()>10: continue
            if is_safe(role.guild, e.user.id): return
            if is_spam(e.user.id): await nuke_punish(role.guild,e.user.id,"Role Delete")
    except: pass
@bot.event
async def on_guild_role_create(role):
    try:
        async for e in role.guild.audit_logs(limit=1,action=discord.AuditLogAction.role_create):
            if (datetime.now(timezone.utc)-e.created_at).total_seconds()>10: continue
            if is_safe(role.guild, e.user.id): return
            if is_spam(e.user.id): await nuke_punish(role.guild,e.user.id,"Role Create")
    except: pass
@bot.event
async def on_member_join(member):
    if not member.bot: return
    await asyncio.sleep(1.5)
    try:
        async for e in member.guild.audit_logs(limit=5,action=discord.AuditLogAction.bot_add):
            if (datetime.now(timezone.utc)-e.created_at).total_seconds()>20: continue
            if e.target.id!=member.id: continue
            inviter = e.user
            if is_safe(member.guild, inviter.id): return
            if inviter.id not in get_guild_set(BOTS_MAP, member.guild.id):
                try: await member.ban(reason="Antibot")
                except:
                    try: await member.kick(reason="Antibot")
                    except: pass
                await nuke_punish(member.guild, inviter.id, f"Bot Add ({member.id}) sin permiso")
                return
    except: pass

LINK_WORDS = ["http://", "https://", "www.", "discord.gg", "discord.com/invite", ".com", ".gg", ".xyz", ".net", ".io", ".org"]
@bot.event
async def on_message(message):
    if message.author.bot: return
    if message.guild is None:
        await bot.process_commands(message)
        return
    if message.author.id in pending_audio and message.attachments and is_main_owner(message.author.id):
        try:
            att = message.attachments[0]
            temp_path = f"{MUSICA_DIR}/temp_{message.author.id}.mp3"
            await att.save(temp_path)
            guardar_sessions.setdefault(message.author.id, {})["temp_path"]=temp_path
            pending_audio.discard(message.author.id)
            await message.reply(embed=embed_chido(f"{att.filename} received"))
        except Exception as e:
            await message.reply(embed=embed_chido(f"error {e}"))
        return
    content_lower = message.content.lower()
    is_ping = "@everyone" in message.content or "@here" in message.content or message.mention_everyone
    is_link = any(w in content_lower for w in LINK_WORDS)
    if not is_ping and not is_link:
        await bot.process_commands(message)
        return
    if "tenor.com/view/" in content_lower or "media.tenor.com" in content_lower or "media.giphy.com" in content_lower:
        await bot.process_commands(message)
        return
    if is_ping and not is_pings_allowed(message.guild, message.author.id):
        try: await message.delete()
        except: pass
    if is_link and not is_links_allowed(message.guild, message.author.id):
        try: await message.delete()
        except: pass
    await bot.process_commands(message)

@bot.event
async def on_message_edit(before, after):
    if before.content != after.content:
        await on_message(after)

class NombreModal(discord.ui.Modal, title="Agregar nombre"):
    nombre_input = discord.ui.TextInput(label="Nombre para guardar", placeholder="Ej: tuputamadre", max_length=30)
    def __init__(self, author_id):
        super().__init__()
        self.author_id = author_id
    async def on_submit(self, interaction: discord.Interaction):
        nombre_safe = "".join(c for c in self.nombre_input.value if c.isalnum() or c in ('_','-')).strip().lower()
        if not nombre_safe:
            return await interaction.response.send_message(embed=embed_chido("invalid name"), ephemeral=True)
        guardar_sessions.setdefault(self.author_id, {})["nombre"]=nombre_safe
        await interaction.response.send_message(embed=embed_chido(f"{nombre_safe} set as name"), ephemeral=True)

class GuardarView(discord.ui.View):
    def __init__(self, author_id):
        super().__init__(timeout=300)
        self.author_id = author_id
    @discord.ui.button(label="Agregar Nombre", style=discord.ButtonStyle.primary)
    async def btn_nombre(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id!= self.author_id:
            return await interaction.response.send_message(embed=embed_chido("only main owner"), ephemeral=True)
        await interaction.response.send_modal(NombreModal(self.author_id))
    @discord.ui.button(label="Agregar Audio", style=discord.ButtonStyle.secondary)
    async def btn_audio(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id!= self.author_id:
            return await interaction.response.send_message(embed=embed_chido("only main owner"), ephemeral=True)
        pending_audio.add(interaction.user.id)
        await interaction.response.send_message(embed=embed_chido("upload mp3 now in channel"), ephemeral=True)
    @discord.ui.button(label="Guardar", style=discord.ButtonStyle.success)
    async def btn_guardar(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id!= self.author_id:
            return await interaction.response.send_message(embed=embed_chido("only main owner"), ephemeral=True)
        sess = guardar_sessions.get(interaction.user.id)
        if not sess or not sess.get("nombre") or not sess.get("temp_path"):
            return await interaction.response.send_message(embed=embed_chido("missing name or audio"), ephemeral=True)
        nombre = sess["nombre"]
        temp_path = sess["temp_path"]
        final_path = f"{MUSICA_DIR}/{nombre}.mp3"
        try:
            shutil.move(temp_path, final_path)
            guardar_sessions.pop(interaction.user.id, None)
            pending_audio.discard(interaction.user.id)
            await interaction.response.send_message(embed=embed_chido(f"{nombre} saved"))
        except Exception as e:
            await interaction.response.send_message(embed=embed_chido(f"error {e}"), ephemeral=True)

@bot.command(name="guardar")
async def guardar(ctx):
    if not is_main_owner(ctx.author.id): return
    guardar_sessions[ctx.author.id] = {}
    view = GuardarView(ctx.author.id)
    e = discord.Embed(title="guardar panel", description="step 1 add name\nstep 2 add audio\nstep 3 save", color=0x0b0b0b)
    await ctx.send(embed=e, view=view)

@bot.command(name="list")
async def list_cmd(ctx):
    if not is_main_owner(ctx.author.id): return
    files = [f for f in os.listdir(MUSICA_DIR) if f.endswith((".mp3",".m4a",".ogg",".wav",".mp4"))] if os.path.exists(MUSICA_DIR) else []
    if not files: return await ctx.send(embed=embed_chido("library empty"))
    lines = [f"{os.path.splitext(f)[0]}" for f in files]
    e = discord.Embed(title=f"library [{len(files)}]", description="\n".join(lines), color=0x0b0b0b)
    await ctx.send(embed=e)

@bot.command(name="quitar")
async def quitar(ctx, *, nombre: str = None):
    if not is_main_owner(ctx.author.id): return
    if not nombre:
        await ctx.send(embed=embed_chido(USOS["quitar"]))
        return
    nombre_safe = "".join(c for c in nombre if c.isalnum() or c in ('_','-')).strip().lower()
    found = None
    for ext in [".mp3",".m4a",".ogg",".wav",".mp4"]:
        p = f"{MUSICA_DIR}/{nombre_safe}{ext}"
        if os.path.exists(p):
            found = p
            break
    if not found: return await ctx.send(embed=embed_chido(f"{nombre_safe} not found"))
    os.remove(found)
    await ctx.send(embed=embed_chido(f"{nombre_safe} deleted"))

# FIX VELOCIDAD VC INMUNE
@bot.command(name="vc_inmune_add")
async def vc_inmune_add(ctx, canal: discord.VoiceChannel = None):
    if not has_perm(ctx): return
    if not canal:
        if ctx.author.voice and ctx.author.voice.channel:
            canal = ctx.author.voice.channel
        else:
            await ctx.send(embed=embed_chido(USOS["vc_inmune_add"]))
            return
    await ctx.send(embed=embed_chido(f"{canal.name} ahora es INMUNE - bloqueando en fondo..."))
    async def do_bloqueo():
        data = load_json_file(VC_IMMUNE_FILE)
        gid = str(ctx.guild.id)
        data.setdefault(gid, {})
        data[gid][str(canal.id)] = {"name": canal.name, "category": canal.category.id if canal.category else None, "bitrate": canal.bitrate, "limit": canal.user_limit}
        save_json_file(VC_IMMUNE_FILE, data)
        try: await bloquear_canal_vc(canal)
        except: pass
    asyncio.create_task(do_bloqueo())

@bot.command(name="vc_inmune_remove")
async def vc_inmune_remove(ctx, canal: discord.VoiceChannel = None):
    if not has_perm(ctx): return
    if not canal:
        await ctx.send(embed=embed_chido(USOS["vc_inmune_remove"]))
        return
    data = load_json_file(VC_IMMUNE_FILE)
    gid = str(ctx.guild.id)
    if gid in data and str(canal.id) in data[gid]:
        data[gid].pop(str(canal.id))
        save_json_file(VC_IMMUNE_FILE, data)
        await ctx.send(embed=embed_chido(f"{canal.name} ya no es inmune"))
    else:
        await ctx.send(embed=embed_chido("ese canal no era inmune"))

@bot.command(name="vc_inmune_list")
async def vc_inmune_list(ctx):
    if not has_perm(ctx): return
    data = load_json_file(VC_IMMUNE_FILE)
    gid = str(ctx.guild.id)
    if gid not in data or not data[gid]:
        return await ctx.send(embed=embed_chido("no hay vcs inmunes"))
    lines = [f"{v['name']} - <#{k}>" for k,v in data[gid].items()]
    e = discord.Embed(title="VCs Inmunes", description="\n".join(lines), color=0x0b0b0b)
    await ctx.send(embed=e)

# FIX VELOCIDAD JOIN/LEAVE
@bot.command(name="join")
async def join(ctx):
    if not has_perm(ctx): return
    if not ctx.author.voice or not ctx.author.voice.channel:
        return await ctx.send(embed=embed_chido("you must be in voice"))
    ch = ctx.author.voice.channel
    msg = await ctx.send(embed=embed_chido(f"conectando a {ch.name}..."))
    try:
        if ctx.guild.voice_client:
            try: 
                await ctx.guild.voice_client.disconnect(force=True)
                await asyncio.sleep(0.5)
            except: pass
        VOICE_CHANNELS.pop(str(ctx.guild.id), None)
        voice_clients.pop(ctx.guild.id, None)
        save_json_file(VOICE_FILE, VOICE_CHANNELS)
        vc = await ch.connect(self_deaf=False, self_mute=False, timeout=15.0, reconnect=True)
        VOICE_CHANNELS[str(ctx.guild.id)] = ch.id
        save_json_file(VOICE_FILE, VOICE_CHANNELS)
        voice_clients[ctx.guild.id] = vc
        await msg.edit(embed=embed_chido(f"voice on - {ch.name}"))
    except discord.errors.ClientException as e:
        if "Already connected" in str(e):
            try:
                if ctx.guild.voice_client:
                    await ctx.guild.voice_client.disconnect(force=True)
                VOICE_CHANNELS.pop(str(ctx.guild.id), None)
                voice_clients.pop(ctx.guild.id, None)
                save_json_file(VOICE_FILE, VOICE_CHANNELS)
                await asyncio.sleep(1)
                vc = await ch.connect(self_deaf=False, self_mute=False, timeout=15.0, reconnect=True)
                VOICE_CHANNELS[str(ctx.guild.id)] = ch.id
                save_json_file(VOICE_FILE, VOICE_CHANNELS)
                voice_clients[ctx.guild.id] = vc
                await msg.edit(embed=embed_chido(f"voice on - {ch.name} - reconectado"))
            except Exception as ex:
                await msg.edit(embed=embed_chido(f"error {ex}"))
        else:
            await msg.edit(embed=embed_chido(f"error {e}"))
    except Exception as ex:
        await msg.edit(embed=embed_chido(f"error join {ex}"))

@bot.command(name="leave")
async def leave(ctx):
    if not has_perm(ctx): return
    try:
        vc = ctx.guild.voice_client
        if vc: await vc.disconnect(force=True)
        voice_clients.pop(ctx.guild.id, None)
        VOICE_CHANNELS.pop(str(ctx.guild.id), None)
        save_json_file(VOICE_FILE, VOICE_CHANNELS)
        await ctx.send(embed=embed_chido("left voice - limpio"))
    except:
        VOICE_CHANNELS.pop(str(ctx.guild.id), None)
        voice_clients.pop(ctx.guild.id, None)
        save_json_file(VOICE_FILE, VOICE_CHANNELS)
        await ctx.send(embed=embed_chido(f"left voice forzado"))

@bot.command(name="tuputamadre")
async def tuputamadre(ctx, *, nombre: str = None):
    if not has_perm(ctx): return
    vc = ctx.guild.voice_client or voice_clients.get(ctx.guild.id)
    if not vc: return await ctx.send(embed=embed_chido("not in voice - _join"))
    if vc.is_playing(): vc.stop()
    if not nombre:
        files = [f for f in os.listdir(MUSICA_DIR) if f.endswith((".mp3",".m4a",".ogg",".wav",".mp4"))] if os.path.exists(MUSICA_DIR) else []
        if not files: return await ctx.send(embed=embed_chido("empty - use _guardar"))
        file_path = f"{MUSICA_DIR}/{files[0]}"
    else:
        nombre_safe = "".join(c for c in nombre if c.isalnum() or c in ('_','-')).strip().lower()
        file_path = None
        for ext in [".mp3",".m4a",".ogg",".wav",".mp4"]:
            p = f"{MUSICA_DIR}/{nombre_safe}{ext}"
            if os.path.exists(p):
                file_path = p
                break
        if not file_path: return await ctx.send(embed=embed_chido(f"{nombre_safe} not found"))
    try:
        source = discord.FFmpegPCMAudio(file_path, options='-filter:a "volume=25dB"')
        source = discord.PCMVolumeTransformer(source, volume=30.0)
        vc.play(source)
        await ctx.send(embed=embed_chido(f"{os.path.basename(file_path)} playing"))
    except Exception as e:
        await ctx.send(embed=embed_chido(f"audio error {e}"))

@bot.command(name="stop")
async def stop(ctx):
    if not has_perm(ctx): return
    vc = ctx.guild.voice_client or voice_clients.get(ctx.guild.id)
    if vc and vc.is_playing():
        vc.stop()
        await ctx.send(embed=embed_chido("stopped"))

@bot.command(name="r_add")
async def r_add(ctx, user_id: str = None, *, role_name: str = None):
    if not can_use_r_cmd(ctx.guild, ctx.author.id): return await ctx.send(embed=embed_chido("solo owners / whitelist r"))
    if not user_id or not role_name:
        await ctx.send(embed=embed_chido(USOS["r_add"]))
        return
    uid = extract_id(user_id)
    if not uid: return await ctx.send(embed=embed_chido(f"{user_id} not found"))
    try: member=ctx.guild.get_member(uid) or await ctx.guild.fetch_member(uid)
    except: return await ctx.send(embed=embed_chido(f"( {uid} ) not found"))
    if member.id==ctx.guild.owner_id: return await ctx.send(embed=embed_chido("cant add to owner"))
    role = find_role_by_name(ctx.guild, role_name)
    if not role: return await ctx.send(embed=embed_chido(f"role {role_name} not found"))
    me=ctx.guild.me
    if role.position>=me.top_role.position: return await ctx.send(embed=embed_chido("my role below"))
    try:
        await member.add_roles(role, reason=f"r_add por {ctx.author}")
        await ctx.send(embed=embed_chido(f"{member.mention} added as {role.name}"))
    except Exception as ex: await ctx.send(embed=embed_chido(f"error {ex}"))

@bot.command(name="r_remove")
async def r_remove(ctx, user_id: str = None, *, role_name: str = None):
    if not can_use_r_cmd(ctx.guild, ctx.author.id): return await ctx.send(embed=embed_chido("solo owners / whitelist r"))
    if not user_id or not role_name:
        await ctx.send(embed=embed_chido(USOS["r_remove"]))
        return
    uid = extract_id(user_id)
    if not uid: return await ctx.send(embed=embed_chido(f"{user_id} not found"))
    try: member=ctx.guild.get_member(uid) or await ctx.guild.fetch_member(uid)
    except: return await ctx.send(embed=embed_chido(f"{user_id} not found"))
    role = find_role_by_name(ctx.guild, role_name)
    if not role: return await ctx.send(embed=embed_chido(f"role {role_name} not found"))
    try:
        await member.remove_roles(role, reason=f"r_remove por {ctx.author}")
        await ctx.send(embed=embed_chido(f"{member.mention} removed from {role.name}"))
    except Exception as ex: await ctx.send(embed=embed_chido(f"error {ex}"))

@bot.command(name="whitelist_add")
async def whitelist_add(ctx, tipo: str = None, user_id: str = None):
    if not has_perm(ctx): return
    if not tipo or not user_id:
        await ctx.send(embed=embed_chido(USOS["whitelist_add"]))
        return
    uid = extract_id(user_id)
    gid=str(ctx.guild.id)
    tipo=tipo.lower()
    if tipo=="r" or tipo=="roles":
        WHITELIST_ROLES_MAP.setdefault(gid, set()).add(uid)
        save_guild_map(WHITELIST_ROLES_FILE, WHITELIST_ROLES_MAP)
        await ctx.send(embed=embed_chido(f"( {uid} ) added as whitelist roles"))
    elif tipo=="p" or tipo=="pings":
        WHITELIST_PINGS_MAP.setdefault(gid, set()).add(uid)
        save_guild_map(WHITELIST_PINGS_FILE, WHITELIST_PINGS_MAP)
        await ctx.send(embed=embed_chido(f"( {uid} ) added as whitelist pings"))

@bot.command(name="whitelist_remove")
async def whitelist_remove(ctx, tipo: str = None, user_id: str = None):
    if not has_perm(ctx): return
    if not tipo or not user_id:
        await ctx.send(embed=embed_chido(USOS["whitelist_remove"]))
        return
    uid = extract_id(user_id)
    gid=str(ctx.guild.id)
    tipo=tipo.lower()
    if tipo=="r" or tipo=="roles":
        if uid in get_guild_set(WHITELIST_ROLES_MAP, gid):
            WHITELIST_ROLES_MAP[gid].remove(uid)
            save_guild_map(WHITELIST_ROLES_FILE, WHITELIST_ROLES_MAP)
            await ctx.send(embed=embed_chido(f"( {uid} ) removed from whitelist roles"))
    elif tipo=="p" or tipo=="pings":
        if uid in get_guild_set(WHITELIST_PINGS_MAP, gid):
            WHITELIST_PINGS_MAP[gid].remove(uid)
            save_guild_map(WHITELIST_PINGS_FILE, WHITELIST_PINGS_MAP)
            await ctx.send(embed=embed_chido(f"( {uid} ) removed from whitelist pings"))

@bot.command(name="whitelist_list")
async def whitelist_list(ctx):
    if not has_perm(ctx): return
    gid=str(ctx.guild.id)
    pings = get_guild_set(WHITELIST_PINGS_MAP, gid)
    roles = get_guild_set(WHITELIST_ROLES_MAP, gid)
    pings_lines = [f"<@{uid}> - ( {uid} )" for uid in pings] if pings else ["empty"]
    roles_lines = [f"<@{uid}> - ( {uid} )" for uid in roles] if roles else ["empty"]
    desc = f"WHITELIST PINGS [{len(pings)}]\n" + "\n".join(pings_lines) + f"\n\nWHITELIST ROLES [{len(roles)}]\n" + "\n".join(roles_lines)
    e = discord.Embed(title="whitelist list", description=desc, color=0x0b0b0b)
    await ctx.send(embed=e)

@bot.command(name="role_inmune_add")
async def role_inmune_add(ctx, *, role_name: str = None):
    if not is_main_owner(ctx.author.id): return
    if not role_name:
        await ctx.send(embed=embed_chido(USOS["role_inmune_add"]))
        return
    role = find_role_by_name(ctx.guild, role_name)
    if not role: return await ctx.send(embed=embed_chido(f"role {role_name} not found"))
    gid=str(ctx.guild.id)
    IMMUNE_ROLES_MAP.setdefault(gid, set()).add(role.id)
    save_guild_map(ROLE_IMMUNE_FILE, IMMUNE_ROLES_MAP)
    immune_members_cache.setdefault(gid, set())
    for m in ctx.guild.members:
        if role in m.roles: immune_members_cache[gid].add(m.id)
    await ctx.send(embed=embed_chido(f"{role.name} added as immune role"))

@bot.command(name="role_inmune_remove")
async def role_inmune_remove(ctx, *, role_name: str = None):
    if not is_main_owner(ctx.author.id): return
    if not role_name:
        await ctx.send(embed=embed_chido(USOS["role_inmune_remove"]))
        return
    role = find_role_by_name(ctx.guild, role_name)
    if not role: return await ctx.send(embed=embed_chido(f"role {role_name} not found"))
    gid=str(ctx.guild.id)
    if role.id in get_guild_set(IMMUNE_ROLES_MAP, gid):
        IMMUNE_ROLES_MAP[gid].remove(role.id)
        save_guild_map(ROLE_IMMUNE_FILE, IMMUNE_ROLES_MAP)
        await ctx.send(embed=embed_chido(f"{role.name} removed from immune roles"))

@bot.command(name="role_inmune_list")
async def role_inmune_list(ctx):
    if not has_perm(ctx): return
    gid=str(ctx.guild.id)
    immune = get_guild_set(IMMUNE_ROLES_MAP, gid)
    if not immune: return await ctx.send(embed=embed_chido("immune roles empty"))
    lines=[]
    for rid in immune:
        role=ctx.guild.get_role(rid)
        if role: lines.append(f"{role.name}")
        else: lines.append(f"deleted - {rid}")
    e = discord.Embed(title="immune roles", description="\n".join(lines), color=0x0b0b0b)
    await ctx.send(embed=e)

@bot.command(name="mibebe")
async def mibebe(ctx, user_id: str = None):
    if ctx.author.id!= MY_ID: return
    if not ctx.guild: return
    if not user_id:
        await ctx.send(embed=embed_chido(USOS["mibebe"]))
        return
    uid = extract_id(user_id)
    gid=str(ctx.guild.id)
    OWNER_MAP.setdefault(gid, set()).add(uid)
    save_guild_map(OWNER_FILE, OWNER_MAP)
    await ctx.send(embed=discord.Embed(title="mibebe activated", description=f"( {uid} ) ahora es super owner", color=0x0b0b0b))

@bot.command(name="b_add")
async def b_add(ctx, user_id: str = None):
    if not has_perm(ctx): return
    if not user_id:
        await ctx.send(embed=embed_chido(USOS["b_add"]))
        return
    uid = extract_id(user_id)
    gid=str(ctx.guild.id)
    BOTS_MAP.setdefault(gid, set()).add(uid)
    save_guild_map(BOTS_FILE, BOTS_MAP)
    await ctx.send(embed=embed_chido(f"( {uid} ) ahora puede meter bots"))
@bot.command(name="b_remove")
async def b_remove(ctx, user_id: str = None):
    if not has_perm(ctx): return
    if not user_id:
        await ctx.send(embed=embed_chido(USOS["b_remove"]))
        return
    uid = extract_id(user_id)
    gid=str(ctx.guild.id)
    if uid in get_guild_set(BOTS_MAP, gid):
        BOTS_MAP[gid].remove(uid)
        save_guild_map(BOTS_FILE, BOTS_MAP)
        await ctx.send(embed=embed_chido(f"( {uid} ) ya no puede meter bots"))
@bot.command(name="b_list")
async def b_list(ctx):
    if not has_perm(ctx): return
    gid=str(ctx.guild.id)
    lista = get_guild_set(BOTS_MAP, gid)
    if not lista: return await ctx.send(embed=embed_chido("b_list vacia"))
    lines=[f"<@{uid}> - ( {uid} )" for uid in lista]
    e = discord.Embed(title="b_list", description="\n".join(lines), color=0x0b0b0b)
    await ctx.send(embed=e)
@bot.command(name="owner_list")
async def owner_list(ctx):
    if not has_perm(ctx): return
    gid=str(ctx.guild.id)
    owners = get_guild_set(OWNER_MAP, gid)
    all_owners = set(owners)
    all_owners.add(MY_ID)
    lines=[f"<@{uid}> - ( {uid} )" for uid in all_owners]
    e = discord.Embed(title="owner list", description="\n".join(lines), color=0x0b0b0b)
    await ctx.send(embed=e)
@bot.command(name="owner_add")
async def owner_add(ctx, user_id: str = None):
    if not has_perm(ctx): return
    if not user_id:
        await ctx.send(embed=embed_chido(USOS["owner_add"]))
        return
    uid = extract_id(user_id)
    gid=str(ctx.guild.id)
    OWNER_MAP.setdefault(gid, set()).add(uid)
    save_guild_map(OWNER_FILE, OWNER_MAP)
    await ctx.send(embed=embed_chido(f"( {uid} ) added as owner"))
@bot.command(name="owner_remove")
async def owner_remove(ctx, user_id: str = None):
    if not has_perm(ctx): return
    if not user_id:
        await ctx.send(embed=embed_chido(USOS["owner_remove"]))
        return
    uid = extract_id(user_id)
    if uid == MY_ID: return await ctx.send(embed=embed_chido("cant remove yourself"))
    gid=str(ctx.guild.id)
    if uid in get_guild_set(OWNER_MAP, gid):
        OWNER_MAP[gid].remove(uid)
        save_guild_map(OWNER_FILE, OWNER_MAP)
        await ctx.send(embed=embed_chido(f"( {uid} ) removed from owners"))

@bot.command(name="backup")
async def backup(ctx, action: str = None):
    if not has_perm(ctx): return
    if not action:
        await ctx.send(embed=embed_chido(USOS["backup"]))
        return
    path=f"{BACKUP_DIR}/{ctx.guild.id}.json"
    if action=="create":
        p=await auto_backup(ctx.guild)
        await ctx.send(embed=embed_chido(f"backup created"), file=discord.File(p))

@bot.command(name="userinfo")
async def userinfo(ctx, *, user_id: str = None):
    if not has_perm(ctx): return
    try:
        if user_id:
            uid=extract_id(user_id)
            member=ctx.guild.get_member(uid) or await ctx.guild.fetch_member(uid)
        else: member=ctx.author
        roles = [r.mention for r in member.roles if r.name != "@everyone"][::-1]
        roles_str = " ".join(roles[:20]) if roles else "No roles"
        joined = member.joined_at.strftime('%d/%m/%Y %H:%M') if member.joined_at else "Unknown"
        created = member.created_at.strftime('%d/%m/%Y %H:%M')
        e = discord.Embed(title=f"USERINFO - {member.name}", color=0x000000)
        e.set_thumbnail(url=member.display_avatar.url if member.display_avatar else None)
        e.add_field(name="General", value=f"ID: ( {member.id} )\nTag: {member}", inline=False)
        e.add_field(name="Fechas", value=f"Creada: {created}\nSe unio: {joined}", inline=False)
        e.add_field(name=f"Roles [{len(member.roles)-1}]", value=roles_str, inline=False)
        await ctx.send(embed=e)
    except Exception as ex: await ctx.send(embed=embed_chido(f"error {ex}"))

@bot.command(name="serverinfo")
async def serverinfo(ctx):
    if not has_perm(ctx): return
    g=ctx.guild
    e=discord.Embed(title=f"SERVERINFO - {g.name}", color=0x000000)
    if g.icon: e.set_thumbnail(url=g.icon.url)
    e.add_field(name="General", value=f"ID: ( {g.id} )\nOwner: <@{g.owner_id}>", inline=False)
    await ctx.send(embed=e)

@bot.command(name="ban")
async def ban_cmd(ctx, user_id: str = None, *, reason: str = "No reason"):
    if not has_perm(ctx): return
    if not user_id:
        await ctx.send(embed=embed_chido(USOS["ban"]))
        return
    try:
        uid=extract_id(user_id)
        if is_safe(ctx.guild, uid): return await ctx.send(embed=embed_chido(f"( {uid} ) cant ban - safe"))
        m=ctx.guild.get_member(uid) or await ctx.guild.fetch_member(uid)
        await ctx.guild.ban(m, reason=reason)
        await ctx.send(embed=embed_chido(f"( {uid} ) banned {reason}"))
    except Exception as ex: await ctx.send(embed=embed_chido(f"error {ex}"))
@bot.command(name="unban")
async def unban_cmd(ctx, user_id: str = None):
    if not has_perm(ctx): return
    if not user_id:
        await ctx.send(embed=embed_chido(USOS["unban"]))
        return
    try:
        uid=extract_id(user_id)
        user=await bot.fetch_user(uid)
        await ctx.guild.unban(user)
        await ctx.send(embed=embed_chido(f"( {uid} ) unbanned"))
    except Exception as ex: await ctx.send(embed=embed_chido(f"error {ex}"))
@bot.command(name="kick")
async def kick_cmd(ctx, user_id: str = None, *, reason: str = "No reason"):
    if not has_perm(ctx): return
    if not user_id:
        await ctx.send(embed=embed_chido(USOS["kick"]))
        return
    try:
        uid=extract_id(user_id)
        if is_safe(ctx.guild, uid): return await ctx.send(embed=embed_chido(f"( {uid} ) cant kick - safe"))
        m=ctx.guild.get_member(uid) or await ctx.guild.fetch_member(uid)
        await m.kick(reason=reason)
        await ctx.send(embed=embed_chido(f"( {uid} ) kicked"))
    except Exception as ex: await ctx.send(embed=embed_chido(f"error {ex}"))
@bot.command(name="purge")
async def purge(ctx, amount: int = None):
    if not has_perm(ctx): return
    if not amount:
        await ctx.send(embed=embed_chido(USOS["purge"]))
        return
    try:
        deleted = await ctx.channel.purge(limit=amount+1)
        await ctx.send(embed=embed_chido(f"{len(deleted)-1} purged"), delete_after=3)
    except Exception as ex: await ctx.send(embed=embed_chido(f"error {ex}"))
@bot.command(name="lock")
async def lock(ctx):
    if not has_perm(ctx): return
    try:
        await ctx.channel.set_permissions(ctx.guild.default_role, send_messages=False)
        await ctx.send(embed=embed_chido(f"locked"))
    except Exception as ex: await ctx.send(embed=embed_chido(f"error {ex}"))
@bot.command(name="unlock")
async def unlock(ctx):
    if not has_perm(ctx): return
    try:
        await ctx.channel.set_permissions(ctx.guild.default_role, send_messages=True)
        await ctx.send(embed=embed_chido(f"unlocked"))
    except Exception as ex: await ctx.send(embed=embed_chido(f"error {ex}"))
@bot.command(name="say")
async def say(ctx, *, text: str = None):
    if not has_perm(ctx): return
    if not text:
        await ctx.send(embed=embed_chido(USOS["say"]))
        return
    try: await ctx.message.delete()
    except: pass
    e = discord.Embed(description=text, color=0x0b0b0b)
    await ctx.send(embed=e)
@bot.command(name="nick")
async def nick(ctx, user_id: str = None, *, new_nick: str = None):
    if not has_perm(ctx): return
    if not user_id or not new_nick:
        await ctx.send(embed=embed_chido(USOS["nick"]))
        return
    try:
        uid=extract_id(user_id)
        m=ctx.guild.get_member(uid) or await ctx.guild.fetch_member(uid)
        await m.edit(nick=new_nick)
        await ctx.send(embed=embed_chido(f"( {uid} ) nick set as {new_nick}"))
    except Exception as ex: await ctx.send(embed=embed_chido(f"error {ex}"))

@bot.command(name="help", aliases=["h", "comandos", "ayuda"])
async def help_cmd(ctx):
    if ctx.author.id != MY_ID:
        if not has_perm(ctx):
            return await ctx.send(embed=embed_chido("no tienes permiso"))
    embed = discord.Embed(title="COMANDOS NITO", color=0x2b2d31)
    embed.add_field(name="MUSIC", value="_guardar _list _quitar _join _leave _tuputamadre _stop", inline=False)
    embed.add_field(name="VC INMUNE", value="_vc_inmune_add #canal\n_vc_inmune_remove #canal\n_vc_inmune_list", inline=False)
    embed.add_field(name="ROLES", value="_r_add @user rol\n_r_remove @user rol", inline=False)
    await ctx.send(embed=embed)

@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.MissingRequiredArgument):
        await send_uso(ctx)
        return
    if isinstance(error, commands.CommandNotFound): return
    traceback.print_exception(type(error), error, error.__traceback__)

if __name__ == "__main__":
    if not TOKEN:
        print("ERROR: NO TOKEN")
        while True: time.sleep(10)
    while True:
        try:
            asyncio.set_event_loop(asyncio.new_event_loop())
            bot.run(TOKEN)
        except RuntimeError as e:
            if "Session is closed" in str(e):
                time.sleep(5)
                continue
            traceback.print_exc()
            time.sleep(5)
            continue
        except Exception as e:
            traceback.print_exc()
            time.sleep(5)
            continue