import discord
from discord.ext import commands, tasks
import datetime, asyncio

TOKEN = "TOKENCLIENT" # Ne pas toucher ceci et remplacer automatiquement par le main.py
EXPIRY_DATE = "2099-12-31 23:59:59" # Date d'expiration du bot.'

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
bot = commands.Bot(command_prefix="?", intents=intents)

status_cycle = ["En ligne", "Prêt à aider", "Prefix ?"]

def expired():
    return datetime.datetime.utcnow() > datetime.datetime.strptime(EXPIRY_DATE, "%Y-%m-%d %H:%M:%S")

@bot.event
async def on_ready():
    print(f"{bot.user} prêt | Expiration : {EXPIRY_DATE}")
    change_status.start()
    check_expiry.start()

@tasks.loop(seconds=15)
async def change_status():
    current = status_cycle.pop(0)
    await bot.change_presence(activity=discord.Game(current))
    status_cycle.append(current)

@tasks.loop(minutes=1)
async def check_expiry():
    if expired():
        print(f"{bot.user} expiré, déconnexion...")
        await bot.close()

@bot.command()
async def ping(ctx):
    await ctx.send(f"Pong! {round(bot.latency*1000)}ms")

@bot.command()
async def support(ctx):
    await ctx.send("Pour toute aide, contacte le serveur support.")

@bot.command()
async def help(ctx):
    embed = discord.Embed(title="Commandes disponibles", color=0x3498db)
    embed.add_field(name="?ping", value="Test du bot", inline=False)
    embed.add_field(name="?support", value="Lien du support", inline=False)
    embed.add_field(name="?ban", value="Bannir un membre", inline=False)
    embed.add_field(name="?kick", value="Expulser un membre", inline=False)
    await ctx.send(embed=embed)

@bot.command()
async def ban(ctx, member: discord.Member, *, reason=None):
    try:
        await member.ban(reason=reason)
        await ctx.send(f"{member} a été banni.")
    except:
        await ctx.send("Impossible de bannir ce membre.")

@bot.command()
async def kick(ctx, member: discord.Member, *, reason=None):
    try:
        await member.kick(reason=reason)
        await ctx.send(f"{member} a été expulsé.")
    except:
        await ctx.send("Impossible d'expulser ce membre.")

bot.run(TOKEN)