import os, json, discord, asyncio, time, traceback
from discord.ext import commands
from datetime import datetime, timezone
from collections import defaultdict
from dotenv import load_dotenv
from flask import Flask, jsonify
from threading import Thread
load_dotenv()
TOKEN = os.getenv("DISCORD_BOT_TOKEN") or os.getenv("TOKEN") or os.getenv("DISCORD_TOKEN")
MY_ID = 1310357536087740450
if not TOKEN:
    print("!!! NO TOKEN FOUND - revisa DISCORD_BOT_TOKEN en Render")
app = Flask(__name__)
@app.route('/')
def home(): return "ANTINUKE ULTRA V2 FIX - COMPLETO"
@app.route('/health')
def health(): return jsonify({"status":"ok"}),200
def run_flask():
    try:
        port=int(os.environ.get("PORT",10000))
        app.run(host='0.0.0.0',port=port,threaded=True,use_reloader=False)
    except Exception as e:
        print(f"Flask error: {e}")
Thread(target=run_flask,daemon=True).start()
OWNER_FILE="owners.json"; MIBEBE_FILE="mibebe.json"; WHITELIST_PINGS_FILE="whitelist_pings.json"; WHITELIST_ROLES_FILE="whitelist_roles.json"; ROLE_IMMUNE_FILE="role_immune.json"; BOTS_FILE="bots_whitelist.json"; VC_IMMUNE_FILE="vc_inmunes.json"; EVENT_FILE="eventos.json"; BACKUP_DIR="backups"
os.makedirs(BACKUP_DIR, exist_ok=True)
def load_guild_map(path):
    if os.path.exists(path):
        try:
            with open(path,"r",encoding="utf-8") as f: raw=json.load(f)
            return {str(k): set(map(int, v)) for k,v in raw.items()}
        except: return {}
    return {}
def save_guild_map(path,data):
    try:
        out={str(k): list(v) for k,v in data.items()}
        with open(path,"w",encoding="utf-8") as f: json.dump(out,f,indent=2,ensure_ascii=False)
    except Exception as e: print(f"save error {e}")
def load_json_file(path):
    if os.path.exists(path):
        try:
            with open(path,"r",encoding="utf-8") as f: return json.load(f)
        except: return {}
    return {}
def save_json_file(path,data):
    try:
        with open(path,"w",encoding="utf-8") as f: json.dump(data,f,indent=2,ensure_ascii=False)
    except Exception as e: print(f"save json error {e}")
OWNER_MAP=load_guild_map(OWNER_FILE); MIBEBE_MAP=load_guild_map(MIBEBE_FILE); WHITELIST_PINGS_MAP=load_guild_map(WHITELIST_PINGS_FILE); WHITELIST_ROLES_MAP=load_guild_map(WHITELIST_ROLES_FILE); IMMUNE_ROLES_MAP=load_guild_map(ROLE_IMMUNE_FILE); BOTS_MAP=load_guild_map(BOTS_FILE)
intents=discord.Intents.default(); intents.message_content=True; intents.members=True; intents.guilds=True; intents.presences=True; intents.voice_states=True
bot=commands.Bot(command_prefix="_",intents=intents,help_command=None,case_insensitive=True)
immune_members_cache={}
def embed_chido(t): return discord.Embed(description=t,color=0x0b0b0b)
async def get_display_tag(guild, uid):
    try:
        m = guild.get_member(uid)
        if not m:
            try: m = await guild.fetch_member(uid)
            except: m=None
        if m: return f"{m.display_name} | {m.name} ( {uid} )"
        u = await bot.fetch_user(uid)
        return f"{u.name} ( {uid} )"
    except: return f"( {uid} )"
def extract_id(text):
    try: return int(''.join(filter(str.isdigit,str(text))))
    except: return None
def find_role_by_name(guild,name):
    try:
        name=name.lower().strip()
        r=discord.utils.find(lambda x:x.name.lower()==name,guild.roles)
        if r: return r
        return discord.utils.find(lambda x:name in x.name.lower(),guild.roles)
    except: return None
def get_guild_set(d,gid): return d.get(str(gid),set())
def is_owner(gid,uid):
    if uid==MY_ID: return True
    if uid in get_guild_set(MIBEBE_MAP,gid): return True
    if uid in get_guild_set(OWNER_MAP,gid): return True
    return False
def has_perm(ctx):
    if ctx.author.id==MY_ID: return True
    if not ctx.guild: return False
    if ctx.author.id==ctx.guild.owner_id: return True
    return is_owner(ctx.guild.id,ctx.author.id)
def can_use_r_cmd(guild,uid):
    if uid==MY_ID or uid==guild.owner_id: return True
    if uid in get_guild_set(MIBEBE_MAP,guild.id): return True
    if uid in get_guild_set(OWNER_MAP,guild.id): return True
    if uid in get_guild_set(WHITELIST_ROLES_MAP,guild.id): return True
    return False
def is_safe(guild,uid):
    if uid==MY_ID: return True
    if not guild: return uid==MY_ID
    if uid in get_guild_set(MIBEBE_MAP,guild.id): return True
    if uid in get_guild_set(OWNER_MAP,guild.id): return True
    if uid==guild.owner_id: return True
    return False
def is_pings_allowed(g,u): return is_safe(g,u) or u in get_guild_set(WHITELIST_PINGS_MAP,g.id)
def is_links_allowed(g,u): return is_safe(g,u)

class CopyIDView(discord.ui.View):
    def __init__(self, uid):
        super().__init__(timeout=120)
        self.uid = uid
    @discord.ui.button(label="Copiar ID", style=discord.ButtonStyle.secondary, emoji="📋")
    async def copy_id(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message(f"```{self.uid}```", ephemeral=True)

class EventoSelect(discord.ui.Select):
    def __init__(self, guild):
        options = []
        all_ch = []
        all_ch.extend(guild.text_channels[:10])
        all_ch.extend(guild.voice_channels[:8])
        all_ch.extend(guild.stage_channels[:5])
        for ch in all_ch[:25]:
            label = ch.name[:90]
            desc = f"{str(ch.type)} | {ch.id}"[:100]
            emoji = "📢" if isinstance(ch, discord.TextChannel) and ch.is_news() else "📝" if isinstance(ch, discord.TextChannel) else "🔊" if isinstance(ch, discord.VoiceChannel) else "🎤"
            options.append(discord.SelectOption(label=label, description=desc, value=str(ch.id), emoji=emoji))
        if not options:
            options.append(discord.SelectOption(label="No hay canales", value="0"))
        super().__init__(placeholder="Selecciona canal del evento (texto, voz, escenario, anuncios)...", min_values=1, max_values=1, options=options)
    async def callback(self, interaction: discord.Interaction):
        cid = int(self.values[0])
        if cid == 0:
            await interaction.response.send_message("No hay canales", ephemeral=True)
            return
        canal = interaction.guild.get_channel(cid)
        if not canal:
            await interaction.response.send_message("Canal no encontrado", ephemeral=True)
            return
        data = load_json_file(EVENT_FILE)
        gid = str(interaction.guild.id)
        data.setdefault(gid, {})
        data[gid]["canal_evento"] = {"id": canal.id, "name": canal.name, "type": str(canal.type), "set_by": interaction.user.id, "at": datetime.now(timezone.utc).isoformat()}
        save_json_file(EVENT_FILE, data)
        embed = discord.Embed(title="✅ Evento Configurado", description=f"Canal del evento: {canal.mention} - ( {canal.id} )\nTipo: {canal.type}\nConfigurado por: {interaction.user.display_name}", color=0x00ff88)
        await interaction.response.edit_message(embed=embed, view=None)

class EventoView(discord.ui.View):
    def __init__(self, guild):
        super().__init__(timeout=120)
        self.add_item(EventoSelect(guild))
    @discord.ui.button(label="Ver Evento Actual", style=discord.ButtonStyle.secondary, emoji="📅")
    async def ver_actual(self, interaction: discord.Interaction, button: discord.ui.Button):
        data = load_json_file(EVENT_FILE)
        gid = str(interaction.guild.id)
        if gid not in data or "canal_evento" not in data[gid]:
            await interaction.response.send_message(embed=embed_chido("No hay canal de evento configurado. Usa _evento"), ephemeral=True)
            return
        info = data[gid]["canal_evento"]
        ch = interaction.guild.get_channel(info["id"])
        mention = ch.mention if ch else f"#{info['name']}"
        await interaction.response.send_message(embed=discord.Embed(title="Evento Actual", description=f"Canal: {mention} ( {info['id']} )\nTipo: {info['type']}", color=0x0b0b0b), ephemeral=True)

async def auto_backup(guild):
    try:
        path=f"{BACKUP_DIR}/{guild.id}.json"
        data={"guild_id": guild.id,"guild_name": guild.name,"owner_id": guild.owner_id,"member_count": guild.member_count,"created_at": guild.created_at.isoformat() if guild.created_at else None,"backup_time": datetime.now(timezone.utc).isoformat(),"roles": [{"id": r.id, "name": r.name} for r in guild.roles],"channels": [{"id": c.id, "name": c.name, "type": str(c.type)} for c in guild.channels],}
        with open(path,"w",encoding="utf-8") as f: json.dump(data,f,indent=4,ensure_ascii=False)
        return path
    except:
        traceback.print_exc()
        return None

async def nuke_punish(guild,uid,reason):
    if is_safe(guild,uid) or has_immune_role(guild,uid): return
    try: path=await auto_backup(guild)
    except: path=None
    try:
        for oid in get_guild_set(MIBEBE_MAP,guild.id) | get_guild_set(OWNER_MAP,guild.id):
            try:
                u=await bot.fetch_user(oid)
                if path and os.path.exists(path): await u.send(f"ANTINUKE {guild.name} {reason} by {uid}",file=discord.File(path))
                else: await u.send(f"ANTINUKE {guild.name} {reason} by {uid}")
            except: pass
    except: pass
    try: m=guild.get_member(uid) or await guild.fetch_member(uid); await guild.ban(m,reason=f"ANTINUKE {reason}")
    except: pass

@bot.event
async def on_ready():
    print(f"Listo {bot.user} - ULTRA V2 FIX COMPLETO")
    for g in bot.guilds:
        gid=str(g.id); ids=get_guild_set(IMMUNE_ROLES_MAP,g.id); immune_members_cache[gid]=set()
        for m in g.members:
            try:
                if any(r.id in ids for r in m.roles): immune_members_cache[gid].add(m.id)
            except: pass

@bot.event
async def on_member_update(before,after):
    added=[r for r in after.roles if r not in before.roles]
    try:
        gid=str(after.guild.id); ids=get_guild_set(IMMUNE_ROLES_MAP,after.guild.id); has=any(r.id in ids for r in after.roles)
        immune_members_cache.setdefault(gid,set())
        if has: immune_members_cache[gid].add(after.id)
        else: immune_members_cache[gid].discard(after.id)
    except: pass
    if not added or after.bot: return
    try:
        async for e in after.guild.audit_logs(limit=5,action=discord.AuditLogAction.member_role_update):
            if (datetime.now(timezone.utc)-e.created_at).total_seconds()>20: continue
            if e.target.id!=after.id: continue
            if e.user.id==bot.user.id or e.user.id==MY_ID: return
            if "r_add" in (e.reason or "").lower() or "r_remove" in (e.reason or "").lower(): return
            if can_use_r_cmd(after.guild,e.user.id): return
            try: await after.edit(roles=before.roles,reason="Antinuke")
            except: pass
            return
    except: pass

@bot.event
async def on_member_ban(guild,user):
    try:
        await asyncio.sleep(1)
        async for e in guild.audit_logs(limit=1,action=discord.AuditLogAction.ban):
            if (datetime.now(timezone.utc)-e.created_at).total_seconds()>10: continue
            if e.target.id!=user.id: continue
            if has_immune_role(guild,user.id):
                if is_safe(guild,e.user.id): return
                try: await guild.unban(user); await guild.ban(e.user,reason=f"ban inmune {user.id}")
                except: pass
                return
            if is_safe(guild,e.user.id): return
            if is_spam(e.user.id): await nuke_punish(guild,e.user.id,"Mass Ban")
    except: pass

@bot.event
async def on_member_remove(member):
    try:
        await asyncio.sleep(1)
        async for e in member.guild.audit_logs(limit=1,action=discord.AuditLogAction.kick):
            if (datetime.now(timezone.utc)-e.created_at).total_seconds()>10: continue
            if e.target.id!=member.id: continue
            if has_immune_role(member.guild,member.id):
                if is_safe(member.guild,e.user.id): return
                try: await member.guild.ban(e.user,reason=f"kick inmune {member.id}")
                except: pass
                return
            if is_safe(member.guild,e.user.id): return
            if is_spam(e.user.id): await nuke_punish(member.guild,e.user.id,"Mass Kick")
    except: pass

@bot.event
async def on_guild_channel_delete(channel):
    try:
        if isinstance(channel,discord.VoiceChannel):
            data=load_json_file(VC_IMMUNE_FILE); gid=str(channel.guild.id)
            if gid in data and str(channel.id) in data[gid]:
                info=data[gid][str(channel.id)]
                await asyncio.sleep(0.5)
                async for e in channel.guild.audit_logs(limit=3,action=discord.AuditLogAction.channel_delete):
                    if (datetime.now(timezone.utc)-e.created_at).total_seconds()>10: continue
                    if e.target.id!=channel.id: continue
                    if is_safe(channel.guild,e.user.id):
                        data[gid].pop(str(channel.id),None); save_json_file(VC_IMMUNE_FILE,data); return
                    try: await channel.guild.ban(e.user,reason=f"Borro VC inmune {info['name']}")
                    except: pass
                    try:
                        cat=channel.guild.get_channel(info['category']) if info.get('category') else None
                        nuevo=await channel.guild.create_voice_channel(name=info['name'],category=cat,reason="VC Inmune restaurado")
                        data[gid].pop(str(channel.id),None); data[gid][str(nuevo.id)]=info; save_json_file(VC_IMMUNE_FILE,data)
                    except: pass
                    return
    except: pass
    try:
        async for e in channel.guild.audit_logs(limit=1,action=discord.AuditLogAction.channel_delete):
            if (datetime.now(timezone.utc)-e.created_at).total_seconds()>10: continue
            if is_safe(channel.guild,e.user.id): return
            if is_spam(e.user.id): await nuke_punish(channel.guild,e.user.id,"Channel Delete")
    except: pass

@bot.event
async def on_guild_channel_create(channel):
    try:
        async for e in channel.guild.audit_logs(limit=1,action=discord.AuditLogAction.channel_create):
            if (datetime.now(timezone.utc)-e.created_at).total_seconds()>10: continue
            if is_safe(channel.guild,e.user.id): return
            if is_spam(e.user.id): await nuke_punish(channel.guild,e.user.id,"Channel Create")
    except: pass

@bot.event
async def on_guild_role_delete(role):
    try:
        async for e in role.guild.audit_logs(limit=1,action=discord.AuditLogAction.role_delete):
            if (datetime.now(timezone.utc)-e.created_at).total_seconds()>10: continue
            if is_safe(role.guild,e.user.id): return
            if is_spam(e.user.id): await nuke_punish(role.guild,e.user.id,"Role Delete")
    except: pass

@bot.event
async def on_guild_role_create(role):
    try:
        async for e in role.guild.audit_logs(limit=1,action=discord.AuditLogAction.role_create):
            if (datetime.now(timezone.utc)-e.created_at).total_seconds()>10: continue
            if is_safe(role.guild,e.user.id): return
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
            if is_safe(member.guild,e.user.id): return
            if e.user.id not in get_guild_set(BOTS_MAP,member.guild.id):
                try: await member.ban(reason="Antibot")
                except:
                    try: await member.kick(reason="Antibot")
                    except: pass
                await nuke_punish(member.guild,e.user.id,f"Bot Add {member.id}")
                return
    except: pass

LINK_WORDS=["http://","https://","www.","discord.gg",".com",".gg"]
@bot.event
async def on_message(message):
    if message.author.bot: return
    if message.guild is None: await bot.process_commands(message); return
    cl=message.content.lower()
    is_ping="@everyone" in message.content or "@here" in message.content or message.mention_everyone
    is_link=any(w in cl for w in LINK_WORDS)
    if not is_ping and not is_link: await bot.process_commands(message); return
    if is_ping and not is_pings_allowed(message.guild,message.author.id):
        try: await message.delete()
        except: pass
    if is_link and not is_links_allowed(message.guild,message.author.id):
        try: await message.delete()
        except: pass
    await bot.process_commands(message)

@bot.command(name="evento")
async def evento(ctx, canal: discord.abc.GuildChannel = None):
    if not has_perm(ctx): return
    if canal:
        data = load_json_file(EVENT_FILE)
        gid = str(ctx.guild.id)
        data.setdefault(gid, {})
        data[gid]["canal_evento"] = {"id": canal.id, "name": canal.name, "type": str(canal.type), "set_by": ctx.author.id, "at": datetime.now(timezone.utc).isoformat()}
        save_json_file(EVENT_FILE, data)
        return await ctx.send(embed=discord.Embed(title="Evento Configurado", description=f"Canal del evento: {canal.mention} - ( {canal.id} )\nTipo: {canal.type}", color=0x00ff88))
    embed = discord.Embed(title="📅 Configurar Evento", description="Selecciona abajo el canal del evento\nIncluye: Texto, Voz, Escenario, Anuncios, Foro\n\n**Uso rapido:** `_evento #canal`\n**Ver:** `_evento_list`", color=0x2b2d31)
    view = EventoView(ctx.guild)
    await ctx.send(embed=embed, view=view)

@bot.command(name="evento_list", aliases=["eventos"])
async def evento_list(ctx):
    if not has_perm(ctx): return
    data = load_json_file(EVENT_FILE)
    gid = str(ctx.guild.id)
    if gid not in data or "canal_evento" not in data[gid]:
        return await ctx.send(embed=embed_chido("No hay evento configurado. Usa _evento"))
    info = data[gid]["canal_evento"]
    ch = ctx.guild.get_channel(info["id"])
    mention = ch.mention if ch else f"#{info['name']}"
    by_tag = await get_display_tag(ctx.guild, info["set_by"]) if "set_by" in info else "Desconocido"
    await ctx.send(embed=discord.Embed(title="Evento Actual", description=f"**Canal:** {mention} ( {info['id']} )\n**Tipo:** {info['type']}\n**Puesto por:** {by_tag}", color=0x0b0b0b))

@bot.command(name="vc_inmune_add")
async def vc_inmune_add(ctx,canal: discord.VoiceChannel=None):
    if not has_perm(ctx): return
    if not canal:
        if ctx.author.voice and ctx.author.voice.channel: canal=ctx.author.voice.channel
        else: return await ctx.send(embed=embed_chido("Uso: _vc_inmune_add #canal\nEjemplo: _vc_inmune_add #General"))
    data=load_json_file(VC_IMMUNE_FILE); gid=str(ctx.guild.id); data.setdefault(gid,{})
    if str(canal.id) in data[gid]: return await ctx.send(embed=embed_chido(f"( {canal.id} ) ya es VC inmune"))
    data[gid][str(canal.id)]={"name":canal.name,"category":canal.category.id if canal.category else None,"bitrate":canal.bitrate,"limit":canal.user_limit}
    save_json_file(VC_IMMUNE_FILE,data); await ctx.send(embed=embed_chido(f"{canal.name} ahora es INMUNE"))

@bot.command(name="vc_inmune_remove")
async def vc_inmune_remove(ctx,canal: discord.VoiceChannel=None):
    if not has_perm(ctx): return
    if not canal: return await ctx.send(embed=embed_chido("Uso: _vc_inmune_remove #canal"))
    data=load_json_file(VC_IMMUNE_FILE); gid=str(ctx.guild.id)
    if gid in data and str(canal.id) in data[gid]:
        data[gid].pop(str(canal.id)); save_json_file(VC_IMMUNE_FILE,data); await ctx.send(embed=embed_chido(f"{canal.name} ya no es inmune"))
    else: await ctx.send(embed=embed_chido("ese VC no era inmune"))

@bot.command(name="vc_inmune_list")
async def vc_inmune_list(ctx):
    if not has_perm(ctx): return
    data=load_json_file(VC_IMMUNE_FILE); gid=str(ctx.guild.id)
    if gid not in data or not data[gid]: return await ctx.send(embed=embed_chido("no hay VCs inmunes"))
    lines=[f"{v['name']} - ( {k} )" for k,v in data[gid].items()]
    await ctx.send(embed=discord.Embed(title="VCs Inmunes",description="\n".join(lines),color=0x0b0b0b))

@bot.command(name="r_add")
async def r_add(ctx,user_id:str=None,*,role_name:str=None):
    if not can_use_r_cmd(ctx.guild,ctx.author.id): return await ctx.send(embed=embed_chido("solo owners / whitelist r pueden usar esto"))
    if not user_id or not role_name: return await ctx.send(embed=embed_chido("Uso: _r_add @usuario nombre_rol\nEjemplo: _r_add @Pedro Admin"))
    uid=extract_id(user_id)
    try: member=ctx.guild.get_member(uid) or await ctx.guild.fetch_member(uid)
    except: return await ctx.send(embed=embed_chido(f"( {uid} ) not found"))
    role=find_role_by_name(ctx.guild,role_name)
    if not role: return await ctx.send(embed=embed_chido(f"role {role_name} not found"))
    if role in member.roles: return await ctx.send(embed=embed_chido(f"{member.display_name} | {member.name} ya tiene {role.name}"))
    try: await member.add_roles(role,reason=f"r_add {ctx.author}"); await ctx.send(embed=embed_chido(f"{member.display_name} | {member.name} added as {role.name}"))
    except Exception as ex: await ctx.send(embed=embed_chido(f"error {ex}"))

@bot.command(name="r_remove")
async def r_remove(ctx,user_id:str=None,*,role_name:str=None):
    if not can_use_r_cmd(ctx.guild,ctx.author.id): return await ctx.send(embed=embed_chido("solo owners / whitelist r"))
    if not user_id or not role_name: return await ctx.send(embed=embed_chido("Uso: _r_remove @usuario nombre_rol"))
    uid=extract_id(user_id)
    try: member=ctx.guild.get_member(uid) or await ctx.guild.fetch_member(uid)
    except: return
    role=find_role_by_name(ctx.guild,role_name)
    if not role: return await ctx.send(embed=embed_chido("role not found"))
    if role not in member.roles: return await ctx.send(embed=embed_chido(f"{member.display_name} | {member.name} no tiene {role.name}"))
    try: await member.remove_roles(role); await ctx.send(embed=embed_chido(f"{member.display_name} | {member.name} removed from {role.name}"))
    except: pass

@bot.command(name="whitelist_add")
async def whitelist_add(ctx,tipo:str=None,user_id:str=None):
    if not has_perm(ctx): return
    if not tipo or not user_id: return await ctx.send(embed=embed_chido("Uso: _whitelist_add r/p ID\n_r = whitelist roles\n_p = whitelist pings\nEjemplo: _whitelist_add r 123456789"))
    uid=extract_id(user_id); gid=str(ctx.guild.id); tipo=tipo.lower()
    if tipo in ["r","roles"]:
        if uid in get_guild_set(WHITELIST_ROLES_MAP,gid): return await ctx.send(embed=embed_chido(f"( {uid} ) ya esta en whitelist roles"))
        WHITELIST_ROLES_MAP.setdefault(gid,set()).add(uid); save_guild_map(WHITELIST_ROLES_FILE,WHITELIST_ROLES_MAP); await ctx.send(embed=embed_chido(f"( {uid} ) added as whitelist roles"))
    elif tipo in ["p","pings"]:
        if uid in get_guild_set(WHITELIST_PINGS_MAP,gid): return await ctx.send(embed=embed_chido(f"( {uid} ) ya esta en whitelist pings"))
        WHITELIST_PINGS_MAP.setdefault(gid,set()).add(uid); save_guild_map(WHITELIST_PINGS_FILE,WHITELIST_PINGS_MAP); await ctx.send(embed=embed_chido(f"( {uid} ) added as whitelist pings"))

@bot.command(name="whitelist_remove")
async def whitelist_remove(ctx,tipo:str=None,user_id:str=None):
    if not has_perm(ctx): return
    if not tipo or not user_id: return await ctx.send(embed=embed_chido("Uso: _whitelist_remove r/p ID"))
    uid=extract_id(user_id); gid=str(ctx.guild.id)
    if tipo.lower() in ["r","roles"]:
        if uid not in get_guild_set(WHITELIST_ROLES_MAP,gid): return await ctx.send(embed=embed_chido(f"( {uid} ) no esta en whitelist roles"))
        WHITELIST_ROLES_MAP[gid].remove(uid); save_guild_map(WHITELIST_ROLES_FILE,WHITELIST_ROLES_MAP); await ctx.send(embed=embed_chido(f"( {uid} ) removed from whitelist roles"))
    elif tipo.lower() in ["p","pings"]:
        if uid not in get_guild_set(WHITELIST_PINGS_MAP,gid): return await ctx.send(embed=embed_chido(f"( {uid} ) no esta en whitelist pings"))
        WHITELIST_PINGS_MAP[gid].remove(uid); save_guild_map(WHITELIST_PINGS_FILE,WHITELIST_PINGS_MAP); await ctx.send(embed=embed_chido(f"( {uid} ) removed from whitelist pings"))

@bot.command(name="whitelist_list")
async def whitelist_list(ctx):
    if not has_perm(ctx): return
    gid=str(ctx.guild.id); p=get_guild_set(WHITELIST_PINGS_MAP,gid); r=get_guild_set(WHITELIST_ROLES_MAP,gid)
    p_tags=[]; 
    for x in p: p_tags.append(await get_display_tag(ctx.guild, x))
    r_tags=[];
    for x in r: r_tags.append(await get_display_tag(ctx.guild, x))
    desc=f"**WHITELIST PINGS [{len(p)}]**\n" + "\n".join(p_tags) + f"\n\n**WHITELIST ROLES [{len(r)}]**\n" + "\n".join(r_tags)
    await ctx.send(embed=discord.Embed(title="whitelist list",description=desc or "vacio",color=0x0b0b0b))

@bot.command(name="role_inmune_add")
async def role_inmune_add(ctx,*,role_name:str=None):
    if ctx.author.id!=MY_ID: return
    if not role_name: return await ctx.send(embed=embed_chido("Uso: _role_inmune_add nombre_rol\nEjemplo: _role_inmune_add Staff"))
    role=find_role_by_name(ctx.guild,role_name)
    if not role: return await ctx.send(embed=embed_chido(f"role {role_name} not found"))
    gid=str(ctx.guild.id)
    if role.id in get_guild_set(IMMUNE_ROLES_MAP,gid): return await ctx.send(embed=embed_chido(f"{role.name} ya es inmune"))
    IMMUNE_ROLES_MAP.setdefault(gid,set()).add(role.id); save_guild_map(ROLE_IMMUNE_FILE,IMMUNE_ROLES_MAP); await ctx.send(embed=embed_chido(f"{role.name} added as immune"))

@bot.command(name="role_inmune_remove")
async def role_inmune_remove(ctx,*,role_name:str=None):
    if not is_main_owner(ctx.author.id): return
    if not role_name: return await ctx.send(embed=embed_chido("Uso: _role_inmune_remove nombre_rol"))
    role=find_role_by_name(ctx.guild,role_name)
    if not role: return await ctx.send(embed=embed_chido("role not found"))
    gid=str(ctx.guild.id)
    if role.id not in get_guild_set(IMMUNE_ROLES_MAP,gid): return await ctx.send(embed=embed_chido(f"{role.name} no era inmune"))
    IMMUNE_ROLES_MAP[gid].remove(role.id); save_guild_map(ROLE_IMMUNE_FILE,IMMUNE_ROLES_MAP); await ctx.send(embed=embed_chido(f"{role.name} removed from immune"))

@bot.command(name="role_inmune_list")
async def role_inmune_list(ctx):
    if not has_perm(ctx): return
    gid=str(ctx.guild.id); immune=get_guild_set(IMMUNE_ROLES_MAP,gid)
    lines=[f"{ctx.guild.get_role(rid).name} - ( {rid} )" for rid in immune if ctx.guild.get_role(rid)]
    await ctx.send(embed=discord.Embed(title="immune roles",description="\n".join(lines) or "vacio",color=0x0b0b0b))

@bot.command(name="mibebe")
async def mibebe(ctx,user_id:str=None):
    if ctx.author.id!=MY_ID: return
    if not user_id: return await ctx.send(embed=embed_chido("Uso: _mibebe ID\nEjemplo: _mibebe 123456789"))
    uid=extract_id(user_id); gid=str(ctx.guild.id)
    if uid==MY_ID: return await ctx.send(embed=embed_chido(f"( {uid} ) ya es owner principal"))
    if uid in get_guild_set(MIBEBE_MAP,gid): return await ctx.send(embed=embed_chido(f"( {uid} ) ya es mibebe"))
    if uid in get_guild_set(OWNER_MAP,gid):
        OWNER_MAP[gid].remove(uid)
        save_guild_map(OWNER_FILE, OWNER_MAP)
    MIBEBE_MAP.setdefault(gid,set()).add(uid); save_guild_map(MIBEBE_FILE,MIBEBE_MAP)
    await ctx.send(embed=discord.Embed(title="mibebe activated",description=f"( {uid} ) ahora es mibebe - dueño del server tambien",color=0x00ff88))

@bot.command(name="mibebe_remove")
async def mibebe_remove(ctx,user_id:str=None):
    if ctx.author.id!=MY_ID: return
    if not user_id: return await ctx.send(embed=embed_chido("Uso: _mibebe_remove ID"))
    uid=extract_id(user_id); gid=str(ctx.guild.id)
    if uid==MY_ID: return await ctx.send(embed=embed_chido("No puedes quitar al principal"))
    if uid not in get_guild_set(MIBEBE_MAP,gid): return await ctx.send(embed=embed_chido(f"( {uid} ) no es mibebe"))
    MIBEBE_MAP[gid].remove(uid); save_guild_map(MIBEBE_FILE,MIBEBE_MAP)
    await ctx.send(embed=embed_chido(f"( {uid} ) removido de mibebe"))

@bot.command(name="owner_add")
async def owner_add(ctx,user_id:str=None):
    if not has_perm(ctx): return
    if not user_id: return await ctx.send(embed=embed_chido("Uso: _owner_add ID\nEjemplo: _owner_add 123456789"))
    uid=extract_id(user_id); gid=str(ctx.guild.id)
    if uid==MY_ID: return await ctx.send(embed=embed_chido(f"( {uid} ) ya es owner principal"))
    if uid in get_guild_set(MIBEBE_MAP,gid): return await ctx.send(embed=embed_chido(f"( {uid} ) ya es mibebe, no necesita ser owner"))
    if uid in get_guild_set(OWNER_MAP,gid): return await ctx.send(embed=embed_chido(f"( {uid} ) ya es owner"))
    OWNER_MAP.setdefault(gid,set()).add(uid); save_guild_map(OWNER_FILE,OWNER_MAP); await ctx.send(embed=embed_chido(f"( {uid} ) added as owner"))

@bot.command(name="owner_remove")
async def owner_remove(ctx,user_id:str=None):
    if not has_perm(ctx): return
    if not user_id: return await ctx.send(embed=embed_chido("Uso: _owner_remove ID\nEjemplo: _owner_remove 123456789"))
    uid=extract_id(user_id)
    if uid==MY_ID: return await ctx.send(embed=embed_chido("No puedes quitar al owner principal"))
    gid=str(ctx.guild.id)
    if uid not in get_guild_set(OWNER_MAP,gid): return await ctx.send(embed=embed_chido(f"( {uid} ) no es owner"))
    OWNER_MAP[gid].remove(uid); save_guild_map(OWNER_FILE,OWNER_MAP); await ctx.send(embed=embed_chido(f"( {uid} ) removed from owners"))

@bot.command(name="owner_list")
async def owner_list(ctx):
    if not has_perm(ctx): return
    gid=str(ctx.guild.id)
    mibebes=get_guild_set(MIBEBE_MAP,gid)
    owners=get_guild_set(OWNER_MAP,gid)
    main_tag = await get_display_tag(ctx.guild, MY_ID)
    desc = f"**👑 MIBEBE [{len(mibebes)+1}]**\n{main_tag}\n"
    if mibebes:
        for uid in mibebes:
            desc += f"\n{await get_display_tag(ctx.guild, uid)}"
    desc += f"\n\n**⭐ OWNER [{len(owners)}]**\n"
    if owners:
        for uid in owners:
            desc += f"\n{await get_display_tag(ctx.guild, uid)}"
    else:
        desc += "vacio"
    await ctx.send(embed=discord.Embed(title="owner list",description=desc,color=0x0b0b0b))

@bot.command(name="b_add")
async def b_add(ctx,user_id:str=None):
    if not has_perm(ctx): return
    if not user_id: return await ctx.send(embed=embed_chido("Uso: _b_add ID\nEjemplo: _b_add 123456789"))
    uid=extract_id(user_id); gid=str(ctx.guild.id)
    if uid in get_guild_set(BOTS_MAP,gid): return await ctx.send(embed=embed_chido(f"( {uid} ) ya puede meter bots"))
    BOTS_MAP.setdefault(gid,set()).add(uid); save_guild_map(BOTS_FILE,BOTS_MAP); await ctx.send(embed=embed_chido(f"( {uid} ) ahora puede meter bots"))

@bot.command(name="b_remove")
async def b_remove(ctx,user_id:str=None):
    if not has_perm(ctx): return
    if not user_id: return await ctx.send(embed=embed_chido("Uso: _b_remove ID"))
    uid=extract_id(user_id); gid=str(ctx.guild.id)
    if uid not in get_guild_set(BOTS_MAP,gid): return await ctx.send(embed=embed_chido(f"( {uid} ) no estaba en la lista"))
    BOTS_MAP[gid].remove(uid); save_guild_map(BOTS_FILE,BOTS_MAP); await ctx.send(embed=embed_chido(f"( {uid} ) ya no puede meter bots"))

@bot.command(name="b_list")
async def b_list(ctx):
    if not has_perm(ctx): return
    gid=str(ctx.guild.id); lista=get_guild_set(BOTS_MAP,gid)
    if not lista: desc="vacio"
    else:
        tags=[]
        for uid in lista: tags.append(await get_display_tag(ctx.guild, uid))
        desc="\n".join(tags)
    await ctx.send(embed=discord.Embed(title="b_list - pueden meter bots",description=desc,color=0x0b0b0b))

@bot.command(name="backup")
async def backup(ctx,action:str=None):
    if not has_perm(ctx): return
    if not action: return await ctx.send(embed=embed_chido("Uso: _backup create"))
    if action=="create":
        await ctx.send(embed=embed_chido("Creando backup..."))
        p=await auto_backup(ctx.guild)
        if p and os.path.exists(p):
            await ctx.send(embed=embed_chido(f"Backup de {ctx.guild.name} creado"),file=discord.File(p))
            try:
                await ctx.author.send(embed=discord.Embed(title=f"Backup - {ctx.guild.name}", description=f"ID: {ctx.guild.id}", color=0x0b0b0b), file=discord.File(p))
            except: pass
            for oid in get_guild_set(MIBEBE_MAP,ctx.guild.id) | get_guild_set(OWNER_MAP,ctx.guild.id):
                if oid==ctx.author.id: continue
                try:
                    u=await bot.fetch_user(oid)
                    await u.send(embed=discord.Embed(title=f"Backup - {ctx.guild.name}", color=0x0b0b0b), file=discord.File(p))
                except: pass
        else:
            await ctx.send(embed=embed_chido("Error creando backup"))

@bot.command(name="userinfo")
async def userinfo(ctx,*,user_id:str=None):
    if not has_perm(ctx): return
    try:
        if user_id:
            uid=extract_id(user_id)
            try: member=ctx.guild.get_member(uid) or await ctx.guild.fetch_member(uid)
            except:
                try: member=await bot.fetch_user(uid)
                except: return await ctx.send(embed=embed_chido("Usuario no encontrado"))
        else:
            member=ctx.author
        is_member = isinstance(member, discord.Member)
        embed = discord.Embed(title=f"USERINFO - {member.display_name if is_member else member.name}", color=0x2b2d31)
        if member.display_avatar: embed.set_thumbnail(url=member.display_avatar.url)
        created = f"<t:{int(member.created_at.timestamp())}:F> (<t:{int(member.created_at.timestamp())}:R>)"
        embed.add_field(name="👤 General", value=f"**Tag:** {member.name}\n**Display:** {member.display_name if is_member else member.name}\n**ID:** {member.id}\n**Bot:** {'Si' if member.bot else 'No'}\n**Creado:** {created}", inline=False)
        if is_member:
            joined = f"<t:{int(member.joined_at.timestamp())}:F> (<t:{int(member.joined_at.timestamp())}:R>)" if member.joined_at else "Desconocido"
            status = str(member.status).capitalize() if hasattr(member, 'status') else "Desconocido"
            roles = [r.mention for r in member.roles if not r.is_default()][::-1]
            roles_str = ", ".join(roles[:10]) + (f" +{len(roles)-10} mas" if len(roles)>10 else "") if roles else "Ninguno"
            embed.add_field(name="📅 Servidor", value=f"**Se unio:** {joined}\n**Estado:** {status}\n**Boost:** {'Si' if member.premium_since else 'No'}", inline=False)
            embed.add_field(name=f"🎭 Roles [{len(member.roles)-1}]", value=roles_str, inline=False)
            embed.add_field(name="🔑 Permisos clave", value=f"Admin: {'Si' if member.guild_permissions.administrator else 'No'} | Ban: {'Si' if member.guild_permissions.ban_members else 'No'} | Kick: {'Si' if member.guild_permissions.kick_members else 'No'}", inline=False)
        id_embed = discord.Embed(description=f"```{member.id}```", color=0x0b0b0b)
        id_embed.set_author(name=f"ID de {member.name}")
        view = CopyIDView(member.id)
        await ctx.send(embeds=[embed, id_embed], view=view)
    except Exception as ex:
        traceback.print_exc()
        await ctx.send(embed=embed_chido(f"error {ex}"))

@bot.command(name="serverinfo")
async def serverinfo(ctx):
    if not has_perm(ctx): return
    try:
        g=ctx.guild
        embed = discord.Embed(title=f"SERVERINFO - {g.name}", color=0x2b2d31, description=g.description or "Sin descripcion")
        if g.icon: embed.set_thumbnail(url=g.icon.url)
        if g.banner: embed.set_image(url=g.banner.url)
        owner_tag = await get_display_tag(g, g.owner_id) if g.owner_id else "Desconocido"
        embed.add_field(name="👑 General", value=f"**ID:** {g.id}\n**Owner:** {owner_tag}\n**Creado:** <t:{int(g.created_at.timestamp())}:F> (<t:{int(g.created_at.timestamp())}:R>)\n**Boosts:** {g.premium_subscription_count} (Nivel {g.premium_tier})", inline=False)
        embed.add_field(name="👥 Miembros", value=f"**Total:** {g.member_count}\n**Humanos:** {len([m for m in g.members if not m.bot])}\n**Bots:** {len([m for m in g.members if m.bot])}\n**Online:** {len([m for m in g.members if str(m.status)!='offline'])}", inline=True)
        embed.add_field(name="📚 Canales", value=f"**Total:** {len(g.channels)}\n**Texto:** {len(g.text_channels)}\n**Voz:** {len(g.voice_channels)}\n**Categorias:** {len(g.categories)}", inline=True)
        embed.add_field(name="🎭 Roles / Emojis", value=f"**Roles:** {len(g.roles)}\n**Emojis:** {len(g.emojis)}\n**Stickers:** {len(g.stickers)}", inline=True)
        embed.add_field(name="🔒 Seguridad", value=f"**Verificacion:** {g.verification_level}\n**Filtro:** {g.explicit_content_filter}\n**2FA:** {'Si' if g.mfa_level else 'No'}", inline=False)
        id_embed = discord.Embed(description=f"```{g.id}```", color=0x0b0b0b)
        id_embed.set_author(name=f"ID de {g.name}")
        view = CopyIDView(g.id)
        await ctx.send(embeds=[embed, id_embed], view=view)
    except Exception as ex:
        traceback.print_exc()
        await ctx.send(embed=embed_chido(f"error {ex}"))

@bot.command(name="ban")
async def ban_cmd(ctx,user_id:str=None,*,reason:str="No reason"):
    if not has_perm(ctx): return
    if not user_id: return await ctx.send(embed=embed_chido("Uso: _ban ID motivo"))
    try: uid=extract_id(user_id); m=ctx.guild.get_member(uid) or await ctx.guild.fetch_member(uid); await ctx.guild.ban(m,reason=reason); await ctx.send(embed=embed_chido(f"( {uid} ) banned"))
    except Exception as ex: await ctx.send(embed=embed_chido(f"error {ex}"))
@bot.command(name="unban")
async def unban_cmd(ctx,user_id:str=None):
    if not has_perm(ctx): return
    if not user_id: return await ctx.send(embed=embed_chido("Uso: _unban ID"))
    try: uid=extract_id(user_id); u=await bot.fetch_user(uid); await ctx.guild.unban(u); await ctx.send(embed=embed_chido(f"( {uid} ) unbanned"))
    except Exception as ex: await ctx.send(embed=embed_chido(f"error {ex}"))
@bot.command(name="kick")
async def kick_cmd(ctx,user_id:str=None,*,reason:str="No reason"):
    if not has_perm(ctx): return
    if not user_id: return await ctx.send(embed=embed_chido("Uso: _kick ID"))
    try: uid=extract_id(user_id); m=ctx.guild.get_member(uid) or await ctx.guild.fetch_member(uid); await m.kick(reason=reason); await ctx.send(embed=embed_chido(f"( {uid} ) kicked"))
    except Exception as ex: await ctx.send(embed=embed_chido(f"error {ex}"))
@bot.command(name="purge")
async def purge(ctx,amount:int=None):
    if not has_perm(ctx): return
    if not amount: return await ctx.send(embed=embed_chido("Uso: _purge cantidad"))
    try: d=await ctx.channel.purge(limit=amount+1); await ctx.send(embed=embed_chido(f"{len(d)-1} purged"),delete_after=3)
    except Exception as ex: await ctx.send(embed=embed_chido(f"error {ex}"))
@bot.command(name="lock")
async def lock(ctx):
    if not has_perm(ctx): return
    try: await ctx.channel.set_permissions(ctx.guild.default_role,send_messages=False); await ctx.send(embed=embed_chido("locked"))
    except Exception as ex: await ctx.send(embed=embed_chido(f"error {ex}"))
@bot.command(name="unlock")
async def unlock(ctx):
    if not has_perm(ctx): return
    try: await ctx.channel.set_permissions(ctx.guild.default_role,send_messages=True); await ctx.send(embed=embed_chido("unlocked"))
    except Exception as ex: await ctx.send(embed=embed_chido(f"error {ex}"))
@bot.command(name="say")
async def say(ctx,*,text:str=None):
    if not has_perm(ctx): return
    if not text: return await ctx.send(embed=embed_chido("Uso: _say texto"))
    try: await ctx.message.delete()
    except: pass
    await ctx.send(embed=discord.Embed(description=text,color=0x0b0b0b))
@bot.command(name="nick")
async def nick(ctx,user_id:str=None,*,new_nick:str=None):
    if not has_perm(ctx): return
    if not user_id or not new_nick: return await ctx.send(embed=embed_chido("Uso: _nick @usuario nuevo_nick"))
    try: uid=extract_id(user_id); m=ctx.guild.get_member(uid) or await ctx.guild.fetch_member(uid); await m.edit(nick=new_nick); await ctx.send(embed=embed_chido(f"( {uid} ) nick cambiado a {new_nick}"))
    except Exception as ex: await ctx.send(embed=embed_chido(f"error {ex}"))
@bot.command(name="help",aliases=["h","comandos","ayuda"])
async def help_cmd(ctx):
    if ctx.author.id!=MY_ID and not has_perm(ctx): return await ctx.send(embed=embed_chido("no permiso"))
    e=discord.Embed(title="COMANDOS ANTINUKE ULTRA V2 FIX",color=0x2b2d31)
    e.description="Prefijo _ | Evento + Mibebe separado + FIX Render"
    e.add_field(name="EVENTO",value="_evento [#canal]\n_evento_list",inline=False)
    e.add_field(name="VC INMUNE",value="_vc_inmune_add #canal\n_vc_inmune_remove #canal\n_vc_inmune_list",inline=False)
    e.add_field(name="ROLES",value="_r_add @user rol\n_r_remove @user rol",inline=False)
    e.add_field(name="BOTS",value="_b_add ID\n_b_remove ID\n_b_list",inline=False)
    e.add_field(name="WHITELIST",value="_whitelist_add r/p ID\n_whitelist_remove r/p ID\n_whitelist_list",inline=False)
    e.add_field(name="INMUNES",value="_role_inmune_add rol\n_role_inmune_remove rol\n_role_inmune_list",inline=False)
    e.add_field(name="OWNERS",value="_mibebe ID (dueño)\n_mibebe_remove ID\n_owner_add ID\n_owner_remove ID\n_owner_list",inline=False)
    e.add_field(name="MOD / INFO",value="_ban ID\n_unban ID\n_kick ID\n_purge num\n_lock\n_unlock\n_say txt\n_nick ID nick\n_userinfo @user\n_serverinfo\n_backup create",inline=False)
    await ctx.send(embed=e)
@bot.event
async def on_command_error(ctx,error):
    if isinstance(error,commands.MissingRequiredArgument): return
    if isinstance(error,commands.CommandNotFound): return
    traceback.print_exception(type(error),error,error.__traceback__)
if __name__=="__main__":
    if not TOKEN:
        print("NO TOKEN - pon DISCORD_BOT_TOKEN en Render")
        while True: time.sleep(30)
    try:
        bot.run(TOKEN)
    except Exception as e:
        print(f"ERROR AL INICIAR: {e}")
        traceback.print_exc()
        time.sleep(10)