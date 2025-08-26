import discord
from discord.ext import commands, tasks
import json, os, subprocess, sys, platform, shutil, signal, asyncio, datetime

OWNER_ID = 1252377453343543317  # ton ID Discord
BOTS_FILE = "bots_gestion.json"  # fichier de stockage
CLIENT_SCRIPT = "client_template.py"  # template bot client
ROOT_CLIENTS = "clients_bots"  # dossier pour les bots clients
ROLE_PREFIX = "ClientBot"  # préfixe des rôles
ITEMS_PER_PAGE = 5  # bots par page

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
bot = commands.Bot(command_prefix="+", intents=intents)

class BotManager:
    def __init__(self):
        self.bots = self.load_bots()

    def load_bots(self):
        if not os.path.exists(BOTS_FILE): return []
        try:
            with open(BOTS_FILE, "r", encoding="utf-8") as f: return json.load(f)
        except: return []

    def save_bots(self):
        with open(BOTS_FILE, "w", encoding="utf-8") as f: json.dump(self.bots, f, indent=2, ensure_ascii=False)

    async def create_bot(self, token, client_member: discord.Member, days_valid=30):
        bot_id = len(self.bots) + 1
        expiry = datetime.datetime.utcnow() + datetime.timedelta(days=days_valid)
        folder = os.path.join(ROOT_CLIENTS, f"bot_{bot_id}")
        os.makedirs(folder, exist_ok=True)
        with open(os.path.join(folder, "settings.json"), "w") as f: json.dump({}, f)
        with open(CLIENT_SCRIPT, "r", encoding="utf-8") as f: code = f.read()
        code = code.replace("TOKENCLIENT", token).replace("#EXPIRY", f'EXPIRY_DATE="{expiry.strftime("%Y-%m-%d %H:%M:%S")}"')
        with open(os.path.join(folder, "botclient.py"), "w", encoding="utf-8") as f: f.write(code)
        await self.launch_bot(folder)
        self.bots.append({
            "id": bot_id,
            "token": token,
            "client_id": client_member.id,
            "created_at": datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
            "expires_at": expiry.strftime("%Y-%m-%d %H:%M:%S"),
            "folder": folder,
            "active": True
        })
        self.save_bots()
        await self.assign_role(client_member, bot_id)
        return bot_id, expiry

    async def launch_bot(self, folder):
        kwargs = {"cwd": folder}
        if platform.system().lower() == "windows": kwargs['creationflags'] = subprocess.CREATE_NEW_PROCESS_GROUP
        else: kwargs['preexec_fn'] = os.setsid
        proc = subprocess.Popen([sys.executable, "botclient.py"], **kwargs)
        with open(os.path.join(folder, "pid.txt"), "w") as f: f.write(str(proc.pid))
        return proc.pid

    async def kill_bot(self, folder):
        pid_file = os.path.join(folder, "pid.txt")
        if not os.path.exists(pid_file): return False
        try:
            with open(pid_file, "r") as f: pid = int(f.read().strip())
            try: os.kill(pid, signal.SIGTERM)
            except: pass
            await asyncio.sleep(0.5)
            try: os.kill(pid, signal.SIGKILL)
            except: pass
            return True
        except: return False

    async def remove_bot(self, bot_id, guild: discord.Guild):
        bot_info = next((b for b in self.bots if b["id"] == bot_id), None)
        if not bot_info: return False
        killed = await self.kill_bot(bot_info["folder"])
        shutil.rmtree(bot_info["folder"], ignore_errors=True)
        member = guild.get_member(bot_info["client_id"])
        if member: await self.remove_role(member, bot_id)
        self.bots = [b for b in self.bots if b["id"] != bot_id]
        self.save_bots()
        return killed

    async def assign_role(self, member: discord.Member, bot_id):
        role_name = f"{ROLE_PREFIX}_{bot_id}"
        role = discord.utils.get(member.guild.roles, name=role_name)
        if not role: role = await member.guild.create_role(name=role_name, mentionable=True)
        await member.add_roles(role)

    async def remove_role(self, member: discord.Member, bot_id):
        role_name = f"{ROLE_PREFIX}_{bot_id}"
        role = discord.utils.get(member.guild.roles, name=role_name)
        if role:
            try: await member.remove_roles(role)
            except: pass
            try: await role.delete()
            except: pass

    def remaining_days(self, bot_id):
        bot_info = next((b for b in self.bots if b["id"] == bot_id), None)
        if not bot_info: return 0
        expiry = datetime.datetime.strptime(bot_info["expires_at"], "%Y-%m-%d %H:%M:%S")
        return max((expiry - datetime.datetime.utcnow()).days, 0)

manager = BotManager()

def owner_only():
    async def predicate(ctx): return ctx.author.id == OWNER_ID
    return commands.check(predicate)

@bot.command()
@owner_only()
async def ajoutbot(ctx, token: str, jours: int = 30):
    bot_id, expiry = await manager.create_bot(token, ctx.author, jours)
    embed = discord.Embed(title=f"🟢 Bot Client Créé | ID {bot_id}", description=f"Expire le : {expiry.strftime('%Y-%m-%d %H:%M:%S')}", color=0x57f287)
    await ctx.send(embed=embed)

@bot.command()
@owner_only()
async def supprbot(ctx, bot_id: int):
    killed = await manager.remove_bot(bot_id, ctx.guild)
    embed = discord.Embed(title=f"❌ Bot Supprimé | ID {bot_id}", description=f"{'Process tué' if killed else 'Dossier supprimé'}", color=0xe74c3c)
    await ctx.send(embed=embed)

class PaginationView(discord.ui.View):
    def __init__(self, ctx, pages):
        super().__init__(timeout=120)
        self.ctx = ctx
        self.pages = pages
        self.index = 0
    async def update_embed(self, interaction):
        await interaction.response.edit_message(embed=self.pages[self.index], view=self)
    @discord.ui.button(label="⬅️", style=discord.ButtonStyle.blurple)
    async def previous(self, interaction, button):
        self.index = max(self.index - 1, 0)
        await self.update_embed(interaction)
    @discord.ui.button(label="➡️", style=discord.ButtonStyle.blurple)
    async def next(self, interaction, button):
        self.index = min(self.index + 1, len(self.pages) - 1)
        await self.update_embed(interaction)

@bot.command()
async def listebots(ctx):
    bots = manager.bots
    if not bots:
        await ctx.send(embed=discord.Embed(title="📋 Aucun bot trouvé", color=0xe74c3c))
        return
    pages = []
    for i in range(0, len(bots), ITEMS_PER_PAGE):
        embed = discord.Embed(title="📋 Liste des Bots Clients", color=0x3498db)
        for b in bots[i:i+ITEMS_PER_PAGE]:
            days = manager.remaining_days(b["id"])
            status = "🟢 Actif" if b["active"] and days > 0 else "🔴 Expiré"
            embed.add_field(name=f"ID {b['id']} | <@{b['client_id']}> | {status}", value=f"Expire dans {days} jours\nToken: `{b['token'][:7]}...`", inline=False)
        pages.append(embed)
    view = PaginationView(ctx, pages)
    await ctx.send(embed=pages[0], view=view)

status_cycle = ["Gérer les bots clients", "Prefix + | EasyBot", "Regarde mes commandes !"]

@tasks.loop(seconds=15)
async def update_status():
    current = status_cycle.pop(0)
    await bot.change_presence(activity=discord.Game(current))
    status_cycle.append(current)

@tasks.loop(minutes=60)
async def check_expired_bots():  # désactive les bots expirés automatiquement
    for b in manager.bots[:]:
        if manager.remaining_days(b["id"]) <= 0 and b["active"]:
            guild = discord.utils.get(bot.guilds)  # serveur principal
            await manager.remove_bot(b["id"], guild)

@bot.event
async def on_ready():
    print(f"[{datetime.datetime.utcnow().strftime('%H:%M:%S')}] Bot de gestion prêt")
    update_status.start()
    check_expired_bots.start()

bot.run("TON_TOKEN_BOT_GESTION")  # mets ton token ici