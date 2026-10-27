import os, json, discord, asyncio, time
from discord.ext import commands
from datetime import datetime, timezone
from collections import defaultdict
from dotenv import load_dotenv
load_dotenv()

TOKEN = os.getenv("DISCORD_BOT_TOKEN") or os.getenv("TOKEN")
MY_ID = 1310357536087740450  # tu ID dueño principal

intents = discord.Intents.all()
intents.message_content = True
bot = commands.Bot(command_prefix="_", intents=intents, help_command=None)

OWNER_FILE = "owners.json"
if os.path.exists(OWNER_FILE):
    with open(OWNER_FILE,"r") as f:
        OWNER = {str(k): set(map(int,v)) for k,v in json.load(f).items()}
else:
    OWNER = {}

def save_owners():
    with open(OWNER_FILE,"w") as f:
        json.dump({k:list(v) for k,v in OWNER.items()}, f)

def is_owner(gid, uid):
    if uid == MY_ID: return True
    return uid in OWNER.get(str(gid), set())

def is_safe(guild, uid):
    if uid == MY_ID: return True
    if uid in OWNER.get(str(guild.id), set()): return True
    if uid == guild.owner_id: return True
    return False

# antispam
cache = defaultdict(list)
def is_spam(uid):
    now = time.time()
    cache[uid] = [t for t in cache[uid] if now - t < 10]
    cache[uid].append(now)
    return len(cache[uid]) > 3

async def punish(guild, uid, reason):
    if is_safe(guild, uid): return
    try:
        m = guild.get_member(uid) or await guild.fetch_member(uid)
        await guild.ban(m, reason=f"ANTINUKE {reason}")
        print(f"BANEADO {uid} por {reason}")
    except Exception as e:
        print(f"No pude banear {uid}: {e}")

# --- EVENTOS ANTINUKE ---

@bot.event
async def on_ready():
    print(f"ANTINUKE ON - {bot.user}")

@bot.event
async def on_member_ban(guild, user):
    await asyncio.sleep(1)
    try:
        async for e in guild.audit_logs(limit=1, action=discord.AuditLogAction.ban):
            if (datetime.now(timezone.utc)-e.created_at).total_seconds() > 10: continue
            if e.target.id != user.id: continue
            if is_safe(guild, e.user.id): return
            if is_spam(e.user.id):
                await punish(guild, e.user.id, "Mass Ban")
    except: pass

@bot.event
async def on_member_remove(member):
    await asyncio.sleep(1)
    try:
        async for e in member.guild.audit_logs(limit=1, action=discord.AuditLogAction.kick):
            if (datetime.now(timezone.utc)-e.created_at).total_seconds() > 10: continue
            if e.target.id != member.id: continue
            if is_safe(member.guild, e.user.id): return
            if is_spam(e.user.id):
                await punish(member.guild, e.user.id, "Mass Kick")
    except: pass

@bot.event
async def on_guild_channel_delete(channel):
    await asyncio.sleep(1)
    try:
        async for e in channel.guild.audit_logs(limit=1, action=discord.AuditLogAction.channel_delete):
            if (datetime.now(timezone.utc)-e.created_at).total_seconds() > 10: continue
            if e.target.id != channel.id: continue
            if is_safe(channel.guild, e.user.id): return
            if is_spam(e.user.id):
                await punish(channel.guild, e.user.id, "Channel Delete")
    except: pass

@bot.event
async def on_guild_channel_create(channel):
    await asyncio.sleep(1)
    try:
        async for e in channel.guild.audit_logs(limit=1, action=discord.AuditLogAction.channel_create):
            if (datetime.now(timezone.utc)-e.created_at).total_seconds() > 10: continue
            if is_safe(channel.guild, e.user.id): return
            if is_spam(e.user.id):
                await punish(channel.guild, e.user.id, "Channel Create")
    except: pass

@bot.event
async def on_guild_role_delete(role):
    await asyncio.sleep(1)
    try:
        async for e in role.guild.audit_logs(limit=1, action=discord.AuditLogAction.role_delete):
            if (datetime.now(timezone.utc)-e.created_at).total_seconds() > 10: continue
            if is_safe(role.guild, e.user.id): return
            if is_spam(e.user.id):
                await punish(role.guild, e.user.id, "Role Delete")
    except: pass

@bot.event
async def on_guild_role_create(role):
    await asyncio.sleep(1)
    try:
        async for e in role.guild.audit_logs(limit=1, action=discord.AuditLogAction.role_create):
            if (datetime.now(timezone.utc)-e.created_at).total_seconds() > 10: continue
            if is_safe(role.guild, e.user.id): return
            if is_spam(e.user.id):
                await punish(role.guild, e.user.id, "Role Create")
    except: pass

@bot.event
async def on_member_join(member):
    if not member.bot: return
    await asyncio.sleep(2)
    try:
        async for e in member.guild.audit_logs(limit=3, action=discord.AuditLogAction.bot_add):
            if (datetime.now(timezone.utc)-e.created_at).total_seconds() > 15: continue
            if e.target.id != member.id: continue
            if is_safe(member.guild, e.user.id): return
            # banea el bot y al que lo metió
            try: await member.ban(reason="Antibot")
            except: 
                try: await member.kick(reason="Antibot")
                except: pass
            await punish(member.guild, e.user.id, f"Bot Add {member.id}")
    except: pass

# --- COMANDOS SOLO OWNER ---
@bot.command()
async def owner_add(ctx, uid: int):
    if ctx.author.id != MY_ID: return
    OWNER.setdefault(str(ctx.guild.id), set()).add(uid)
    save_owners()
    await ctx.send(f"{uid} ahora es owner")

@bot.command()
async def owner_remove(ctx, uid: int):
    if ctx.author.id != MY_ID: return
    if str(ctx.guild.id) in OWNER and uid in OWNER[str(ctx.guild.id)]:
        OWNER[str(ctx.guild.id)].remove(uid)
        save_owners()
        await ctx.send(f"{uid} removido")
    else:
        await ctx.send("No estaba")

@bot.command()
async def owner_list(ctx):
    owners = OWNER.get(str(ctx.guild.id), set())
    txt = "\n".join([f"<@{x}> - {x}" for x in owners]) if owners else "Vacio"
    await ctx.send(f"Owners:\n{txt}\nPrincipal: <@{MY_ID}>")

bot.run(TOKEN)