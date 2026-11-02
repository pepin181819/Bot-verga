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
app = Flask(__name__)
@app.route('/')
def home(): return "ANTINUKE ON - FINAL LIMPIO"
@app.route('/health')
def health(): return jsonify({"status":"ok"}),200
def run_flask():
    port=int(os.environ.get("PORT",10000))
    app.run(host='0.0.0.0',port=port,threaded=True,use_reloader=False)
Thread(target=run_flask,daemon=True).start()
OWNER_FILE="owners.json"; WHITELIST_PINGS_FILE="whitelist_pings.json"; WHITELIST_ROLES_FILE="whitelist_roles.json"; ROLE_IMMUNE_FILE="role_immune.json"; BOTS_FILE="bots_whitelist.json"; VC_IMMUNE_FILE="vc_inmunes.json"; BACKUP_DIR="backups"
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
    except: pass
def load_json_file(path):
    if os.path.exists(path):
        try:
            with open(path,"r",encoding="utf-8") as f: return json.load(f)
        except: return {}
    return {}
def save_json_file(path,data):
    try:
        with open(path,"w",encoding="utf-8") as f: json.dump(data,f,indent=2,ensure_ascii=False)
    except: pass
OWNER_MAP=load_guild_map(OWNER_FILE); WHITELIST_PINGS_MAP=load_guild_map(WHITELIST_PINGS_FILE); WHITELIST_ROLES_MAP=load_guild_map(WHITELIST_ROLES_FILE); IMMUNE_ROLES_MAP=load_guild_map(ROLE_IMMUNE_FILE); BOTS_MAP=load_guild_map(BOTS_FILE)
intents=discord.Intents.default(); intents.message_content=True; intents.members=True; intents.guilds=True; intents.presences=True; intents.voice_states=True
bot=commands.Bot(command_prefix="_",intents=intents,help_command=None,case_insensitive=True)
immune_members_cache={}
def embed_chido(t): return discord.Embed(description=t,color=0x0b0b0b)
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
def is_main_owner(uid): return uid==MY_ID
def is_owner(gid,uid): return uid==MY_ID or uid in get_guild_set(OWNER_MAP,gid)
def has_perm(ctx):
    if ctx.author.id==MY_ID: return True
    if not ctx.guild: return False
    if ctx.author.id==ctx.guild.owner_id: return True
    return is_owner(ctx.guild.id,ctx.author.id)
def can_use_r_cmd(guild,uid):
    if uid==MY_ID: return True
    if uid==guild.owner_id: return True
    if uid in get_guild_set(OWNER_MAP,guild.id): return True
    if uid in get_guild_set(WHITELIST_ROLES_MAP,guild.id): return True
    return False
LIMIT=3; TIME_WINDOW=10; cache=defaultdict(list)
def is_spam(uid):
    now=time.time(); cache[uid]=[t for t in cache[uid] if now-t<TIME_WINDOW]; cache[uid].append(now); return len(cache[uid])>LIMIT
def has_immune_role(guild,uid):
    try:
        m=guild.get_member(uid)
        if m:
            ids=get_guild_set(IMMUNE_ROLES_MAP,guild.id)
            if any(r.id in ids for r in m.roles): return True
        return uid in immune_members_cache.get(str(guild.id),set())
    except: return False
def is_safe(guild,uid):
    if uid==MY_ID: return True
    if not guild: return uid==MY_ID
    if uid in get_guild_set(OWNER_MAP,guild.id): return True
    if uid==guild.owner_id: return True
    return False
def is_pings_allowed(g,u): return is_safe(g,u) or u in get_guild_set(WHITELIST_PINGS_MAP,g.id)
def is_links_allowed(g,u): return is_safe(g,u)
async def auto_backup(guild):
    try:
        path=f"{BACKUP_DIR}/{guild.id}.json"
        data={"guild_name":guild.name,"guild_id":guild.id,"backup_time":datetime.now(timezone.utc).isoformat()}
        with open(path,"w",encoding="utf-8") as f: json.dump(data,f,indent=4,ensure_ascii=False)
        return path
    except: return None
async def nuke_punish(guild,uid,reason):
    if is_safe(guild,uid) or has_immune_role(guild,uid): return
    try: path=await auto_backup(guild)
    except: path=None
    try:
        for oid in get_guild_set(OWNER_MAP,guild.id):
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
    print(f"Listo {bot.user} - FINAL SIN VC NI MUSICA")
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
@bot.command(name="vc_inmune_add")
async def vc_inmune_add(ctx,canal: discord.VoiceChannel=None):
    if not has_perm(ctx): return
    if not canal:
        if ctx.author.voice and ctx.author.voice.channel: canal=ctx.author.voice.channel
        else: return await ctx.send(embed=embed_chido("Uso: _vc_inmune_add #canal"))
    data=load_json_file(VC_IMMUNE_FILE); gid=str(ctx.guild.id); data.setdefault(gid,{})
    data[gid][str(canal.id)]={"name":canal.name,"category":canal.category.id if canal.category else None,"bitrate":canal.bitrate,"limit":canal.user_limit}
    save_json_file(VC_IMMUNE_FILE,data); await ctx.send(embed=embed_chido(f"{canal.name} INMUNE"))
@bot.command(name="vc_inmune_remove")
async def vc_inmune_remove(ctx,canal: discord.VoiceChannel=None):
    if not has_perm(ctx): return
    if not canal: return await ctx.send(embed=embed_chido("Uso: _vc_inmune_remove #canal"))
    data=load_json_file(VC_IMMUNE_FILE); gid=str(ctx.guild.id)
    if gid in data and str(canal.id) in data[gid]:
        data[gid].pop(str(canal.id)); save_json_file(VC_IMMUNE_FILE,data); await ctx.send(embed=embed_chido(f"{canal.name} ya no inmune"))
    else: await ctx.send(embed=embed_chido("no era inmune"))
@bot.command(name="vc_inmune_list")
async def vc_inmune_list(ctx):
    if not has_perm(ctx): return
    data=load_json_file(VC_IMMUNE_FILE); gid=str(ctx.guild.id)
    if gid not in data or not data[gid]: return await ctx.send(embed=embed_chido("no hay vcs inmunes"))
    lines=[f"{v['name']} - <#{k}>" for k,v in data[gid].items()]
    await ctx.send(embed=discord.Embed(title="VCs Inmunes",description="\n".join(lines),color=0x0b0b0b))
@bot.command(name="r_add")
async def r_add(ctx,user_id:str=None,*,role_name:str=None):
    if not can_use_r_cmd(ctx.guild,ctx.author.id): return await ctx.send(embed=embed_chido("solo owners / whitelist r"))
    if not user_id or not role_name: return await ctx.send(embed=embed_chido("Uso: _r_add @usuario nombre_rol"))
    uid=extract_id(user_id)
    try: member=ctx.guild.get_member(uid) or await ctx.guild.fetch_member(uid)
    except: return await ctx.send(embed=embed_chido("not found"))
    role=find_role_by_name(ctx.guild,role_name)
    if not role: return await ctx.send(embed=embed_chido("role not found"))
    try: await member.add_roles(role,reason=f"r_add {ctx.author}"); await ctx.send(embed=embed_chido(f"{member.mention} added as {role.name}"))
    except Exception as ex: await ctx.send(embed=embed_chido(f"error {ex}"))
@bot.command(name="r_remove")
async def r_remove(ctx,user_id:str=None,*,role_name:str=None):
    if not can_use_r_cmd(ctx.guild,ctx.author.id): return await ctx.send(embed=embed_chido("solo owners / whitelist r"))
    if not user_id or not role_name: return await ctx.send(embed=embed_chido("Uso: _r_remove @usuario nombre_rol"))
    uid=extract_id(user_id)
    try: member=ctx.guild.get_member(uid) or await ctx.guild.fetch_member(uid)
    except: return
    role=find_role_by_name(ctx.guild,role_name)
    if not role: return
    try: await member.remove_roles(role); await ctx.send(embed=embed_chido(f"removed {role.name}"))
    except: pass
@bot.command(name="whitelist_add")
async def whitelist_add(ctx,tipo:str=None,user_id:str=None):
    if not has_perm(ctx): return
    if not tipo or not user_id: return await ctx.send(embed=embed_chido("Uso: _whitelist_add r/p ID"))
    uid=extract_id(user_id); gid=str(ctx.guild.id); tipo=tipo.lower()
    if tipo in ["r","roles"]: WHITELIST_ROLES_MAP.setdefault(gid,set()).add(uid); save_guild_map(WHITELIST_ROLES_FILE,WHITELIST_ROLES_MAP); await ctx.send(embed=embed_chido(f"{uid} whitelist roles"))
    elif tipo in ["p","pings"]: WHITELIST_PINGS_MAP.setdefault(gid,set()).add(uid); save_guild_map(WHITELIST_PINGS_FILE,WHITELIST_PINGS_MAP); await ctx.send(embed=embed_chido(f"{uid} whitelist pings"))
@bot.command(name="whitelist_remove")
async def whitelist_remove(ctx,tipo:str=None,user_id:str=None):
    if not has_perm(ctx): return
    if not tipo or not user_id: return
    uid=extract_id(user_id); gid=str(ctx.guild.id)
    if tipo.lower() in ["r","roles"]:
        if uid in get_guild_set(WHITELIST_ROLES_MAP,gid): WHITELIST_ROLES_MAP[gid].remove(uid); save_guild_map(WHITELIST_ROLES_FILE,WHITELIST_ROLES_MAP); await ctx.send(embed=embed_chido(f"{uid} removed"))
@bot.command(name="whitelist_list")
async def whitelist_list(ctx):
    if not has_perm(ctx): return
    gid=str(ctx.guild.id); p=get_guild_set(WHITELIST_PINGS_MAP,gid); r=get_guild_set(WHITELIST_ROLES_MAP,gid)
    desc=f"PINGS [{len(p)}]\n" + "\n".join([f"<@{x}>" for x in p]) + f"\n\nROLES [{len(r)}]\n" + "\n".join([f"<@{x}>" for x in r])
    await ctx.send(embed=discord.Embed(title="whitelist",description=desc,color=0x0b0b0b))
@bot.command(name="role_inmune_add")
async def role_inmune_add(ctx,*,role_name:str=None):
    if not is_main_owner(ctx.author.id): return
    if not role_name: return await ctx.send(embed=embed_chido("Uso: _role_inmune_add nombre_rol"))
    role=find_role_by_name(ctx.guild,role_name)
    if not role: return
    gid=str(ctx.guild.id); IMMUNE_ROLES_MAP.setdefault(gid,set()).add(role.id); save_guild_map(ROLE_IMMUNE_FILE,IMMUNE_ROLES_MAP); await ctx.send(embed=embed_chido(f"{role.name} inmune"))
@bot.command(name="role_inmune_remove")
async def role_inmune_remove(ctx,*,role_name:str=None):
    if not is_main_owner(ctx.author.id): return
    if not role_name: return
    role=find_role_by_name(ctx.guild,role_name)
    if not role: return
    gid=str(ctx.guild.id)
    if role.id in get_guild_set(IMMUNE_ROLES_MAP,gid): IMMUNE_ROLES_MAP[gid].remove(role.id); save_guild_map(ROLE_IMMUNE_FILE,IMMUNE_ROLES_MAP); await ctx.send(embed=embed_chido(f"{role.name} removed"))
@bot.command(name="role_inmune_list")
async def role_inmune_list(ctx):
    if not has_perm(ctx): return
    gid=str(ctx.guild.id); immune=get_guild_set(IMMUNE_ROLES_MAP,gid)
    lines=[ctx.guild.get_role(rid).name for rid in immune if ctx.guild.get_role(rid)]
    await ctx.send(embed=discord.Embed(title="immune roles",description="\n".join(lines) or "vacio",color=0x0b0b0b))
@bot.command(name="mibebe")
async def mibebe(ctx,user_id:str=None):
    if ctx.author.id!=MY_ID: return
    if not user_id: return await ctx.send(embed=embed_chido("Uso: _mibebe ID"))
    uid=extract_id(user_id); gid=str(ctx.guild.id); OWNER_MAP.setdefault(gid,set()).add(uid); save_guild_map(OWNER_FILE,OWNER_MAP); await ctx.send(embed=embed_chido(f"{uid} super owner"))
@bot.command(name="b_add")
async def b_add(ctx,user_id:str=None):
    if not has_perm(ctx): return
    if not user_id: return await ctx.send(embed=embed_chido("Uso: _b_add ID"))
    uid=extract_id(user_id); gid=str(ctx.guild.id); BOTS_MAP.setdefault(gid,set()).add(uid); save_guild_map(BOTS_FILE,BOTS_MAP); await ctx.send(embed=embed_chido(f"{uid} puede meter bots"))
@bot.command(name="b_remove")
async def b_remove(ctx,user_id:str=None):
    if not has_perm(ctx): return
    uid=extract_id(user_id); gid=str(ctx.guild.id)
    if uid in get_guild_set(BOTS_MAP,gid): BOTS_MAP[gid].remove(uid); save_guild_map(BOTS_FILE,BOTS_MAP); await ctx.send(embed=embed_chido(f"{uid} ya no puede"))
@bot.command(name="b_list")
async def b_list(ctx):
    if not has_perm(ctx): return
    gid=str(ctx.guild.id); lista=get_guild_set(BOTS_MAP,gid)
    await ctx.send(embed=discord.Embed(title="b_list",description="\n".join([f"<@{uid}>" for uid in lista]) or "vacio",color=0x0b0b0b))
@bot.command(name="owner_add")
async def owner_add(ctx,user_id:str=None):
    if not has_perm(ctx): return
    uid=extract_id(user_id); gid=str(ctx.guild.id); OWNER_MAP.setdefault(gid,set()).add(uid); save_guild_map(OWNER_FILE,OWNER_MAP); await ctx.send(embed=embed_chido(f"{uid} owner"))
@bot.command(name="owner_remove")
async def owner_remove(ctx,user_id:str=None):
    if not has_perm(ctx): return
    uid=extract_id(user_id)
    if uid==MY_ID: return await ctx.send(embed=embed_chido("no te puedes quitar"))
    gid=str(ctx.guild.id)
    if uid in get_guild_set(OWNER_MAP,gid): OWNER_MAP[gid].remove(uid); save_guild_map(OWNER_FILE,OWNER_MAP); await ctx.send(embed=embed_chido(f"{uid} removed"))
@bot.command(name="owner_list")
async def owner_list(ctx):
    if not has_perm(ctx): return
    gid=str(ctx.guild.id); owners=get_guild_set(OWNER_MAP,gid); all_owners=set(owners); all_owners.add(MY_ID)
    await ctx.send(embed=discord.Embed(title="owners",description="\n".join([f"<@{uid}>" for uid in all_owners]),color=0x0b0b0b))
@bot.command(name="backup")
async def backup(ctx,action:str=None):
    if not has_perm(ctx): return
    if action!="create": return await ctx.send(embed=embed_chido("Uso: _backup create"))
    p=await auto_backup(ctx.guild)
    if p: await ctx.send(embed=embed_chido("backup creado"),file=discord.File(p))
@bot.command(name="userinfo")
async def userinfo(ctx,*,user_id:str=None):
    if not has_perm(ctx): return
    try:
        if user_id: uid=extract_id(user_id); member=ctx.guild.get_member(uid) or await ctx.guild.fetch_member(uid)
        else: member=ctx.author
        e=discord.Embed(title=f"USERINFO {member.name}",color=0x000000); e.add_field(name="ID",value=str(member.id)); await ctx.send(embed=e)
    except Exception as ex: await ctx.send(embed=embed_chido(f"error {ex}"))
@bot.command(name="serverinfo")
async def serverinfo(ctx):
    if not has_perm(ctx): return
    g=ctx.guild; e=discord.Embed(title=g.name,color=0x000000); e.add_field(name="ID",value=str(g.id)); await ctx.send(embed=e)
@bot.command(name="ban")
async def ban_cmd(ctx,user_id:str=None,*,reason:str="No reason"):
    if not has_perm(ctx): return
    if not user_id: return
    try: uid=extract_id(user_id); m=ctx.guild.get_member(uid) or await ctx.guild.fetch_member(uid); await ctx.guild.ban(m,reason=reason); await ctx.send(embed=embed_chido(f"{uid} banned"))
    except Exception as ex: await ctx.send(embed=embed_chido(f"error {ex}"))
@bot.command(name="unban")
async def unban_cmd(ctx,user_id:str=None):
    if not has_perm(ctx): return
    if not user_id: return
    try: uid=extract_id(user_id); u=await bot.fetch_user(uid); await ctx.guild.unban(u); await ctx.send(embed=embed_chido(f"{uid} unbanned"))
    except Exception as ex: await ctx.send(embed=embed_chido(f"error {ex}"))
@bot.command(name="kick")
async def kick_cmd(ctx,user_id:str=None,*,reason:str="No reason"):
    if not has_perm(ctx): return
    if not user_id: return
    try: uid=extract_id(user_id); m=ctx.guild.get_member(uid) or await ctx.guild.fetch_member(uid); await m.kick(reason=reason); await ctx.send(embed=embed_chido(f"{uid} kicked"))
    except Exception as ex: await ctx.send(embed=embed_chido(f"error {ex}"))
@bot.command(name="purge")
async def purge(ctx,amount:int=None):
    if not has_perm(ctx): return
    if not amount: return
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
    if not text: return
    try: await ctx.message.delete()
    except: pass
    await ctx.send(embed=discord.Embed(description=text,color=0x0b0b0b))
@bot.command(name="nick")
async def nick(ctx,user_id:str=None,*,new_nick:str=None):
    if not has_perm(ctx): return
    if not user_id or not new_nick: return
    try: uid=extract_id(user_id); m=ctx.guild.get_member(uid) or await ctx.guild.fetch_member(uid); await m.edit(nick=new_nick); await ctx.send(embed=embed_chido(f"nick {new_nick}"))
    except Exception as ex: await ctx.send(embed=embed_chido(f"error {ex}"))
@bot.command(name="help",aliases=["h","comandos","ayuda"])
async def help_cmd(ctx):
    if ctx.author.id!=MY_ID and not has_perm(ctx): return await ctx.send(embed=embed_chido("no permiso"))
    e=discord.Embed(title="COMANDOS ANTINUKE FINAL",color=0x2b2d31)
    e.description="Prefijo _ | Sin VC 24/7 | Sin musica"
    e.add_field(name="VC INMUNE",value="_vc_inmune_add #canal\n_vc_inmune_remove #canal\n_vc_inmune_list",inline=False)
    e.add_field(name="ROLES",value="_r_add @user rol\n_r_remove @user rol",inline=False)
    e.add_field(name="BOTS",value="_b_add ID\n_b_remove ID\n_b_list",inline=False)
    e.add_field(name="WHITELIST",value="_whitelist_add r/p ID\n_whitelist_remove r/p ID\n_whitelist_list",inline=False)
    e.add_field(name="INMUNES",value="_role_inmune_add rol\n_role_inmune_remove rol\n_role_inmune_list",inline=False)
    e.add_field(name="OWNERS",value="_mibebe ID\n_owner_add ID\n_owner_remove ID\n_owner_list",inline=False)
    e.add_field(name="MOD",value="_ban ID\n_unban ID\n_kick ID\n_purge num\n_lock\n_unlock\n_say txt\n_nick ID nick",inline=False)
    e.add_field(name="INFO",value="_userinfo\n_serverinfo\n_backup create",inline=False)
    await ctx.send(embed=e)
@bot.event
async def on_command_error(ctx,error):
    if isinstance(error,commands.MissingRequiredArgument): return
    if isinstance(error,commands.CommandNotFound): return
    traceback.print_exception(type(error),error,error.__traceback__)
if __name__=="__main__":
    if not TOKEN:
        print("NO TOKEN")
        while True: time.sleep(10)
    bot.run(TOKEN)