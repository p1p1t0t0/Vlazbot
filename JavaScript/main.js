const fs = require('fs');
const path = require('path');
const { spawn } = require('child_process');
const { Client, GatewayIntentBits, Partials, EmbedBuilder } = require('discord.js');

const OWNER_ID = "1252377453343543317"; // ton ID Discord
const BOTS_FILE = "bots_gestion.json";
const CLIENT_TEMPLATE = "client_template.js";
const ROOT_CLIENTS = "clients_bots";
const ROLE_PREFIX = "ClientBot";

const client = new Client({
    intents: [GatewayIntentBits.Guilds, GatewayIntentBits.GuildMembers, GatewayIntentBits.GuildMessages, GatewayIntentBits.MessageContent],
    partials: [Partials.Channel]
});

let bots = [];
if (fs.existsSync(BOTS_FILE)) bots = JSON.parse(fs.readFileSync(BOTS_FILE, "utf-8"));

function saveBots() {
    fs.writeFileSync(BOTS_FILE, JSON.stringify(bots, null, 2), "utf-8");
}

function remainingDays(expiryStr) {
    const expiry = new Date(expiryStr);
    const now = new Date();
    const delta = expiry - now;
    return Math.max(Math.floor(delta / (1000*60*60*24)), 0);
}

async function giveClientRole(guild, member, botId) {
    let roleName = `${ROLE_PREFIX}_${botId}`;
    let role = guild.roles.cache.find(r => r.name === roleName);
    if (!role) role = await guild.roles.create({ name: roleName, mentionable: true });
    await member.roles.add(role);
}

function launchBot(folder) {
    const botPath = path.join(folder, "botclient.js");
    const proc = spawn("node", [botPath], { cwd: folder, detached: true, stdio: "ignore" });
    fs.writeFileSync(path.join(folder, "pid.txt"), proc.pid.toString(), "utf-8");
    proc.unref();
    return proc.pid;
}

async function createBotClient(token, expiryDate, botId) {
    if (!fs.existsSync(ROOT_CLIENTS)) fs.mkdirSync(ROOT_CLIENTS);
    const folder = path.join(ROOT_CLIENTS, `bot_${botId}`);
    if (!fs.existsSync(folder)) fs.mkdirSync(folder);

    let code = fs.readFileSync(CLIENT_TEMPLATE, "utf-8");
    code = code.replace("TOKENCLIENT", token).replace("2099-12-31 23:59:59", expiryDate);
    fs.writeFileSync(path.join(folder, "botclient.js"), code, "utf-8");
    launchBot(folder);
    return folder;
}

async function removeBot(botId, guild) {
    const botInfo = bots.find(b => b.id === botId);
    if (!botInfo) return false;
    const folder = botInfo.folder;

    if (fs.existsSync(path.join(folder, "pid.txt"))) {
        const pid = parseInt(fs.readFileSync(path.join(folder, "pid.txt"), "utf-8"));
        try { process.kill(pid); } catch {}
    }
    fs.rmSync(folder, { recursive: true, force: true });

    const member = guild.members.cache.get(botInfo.clientId);
    if (member) {
        const roleName = `${ROLE_PREFIX}_${botId}`;
        const role = guild.roles.cache.find(r => r.name === roleName);
        if (role) {
            try { await member.roles.remove(role); } catch {}
            try { await role.delete(); } catch {}
        }
    }
    bots = bots.filter(b => b.id !== botId);
    saveBots();
    return true;
}

client.on('messageCreate', async message => {
    if (!message.guild || message.author.bot) return;
    if (message.author.id != OWNER_ID) return;

    const args = message.content.trim().split(/ +/g);
    const cmd = args.shift().toLowerCase();

    if (cmd === "+ajoutbot") {
        const user = message.mentions.users.first();
        const token = args[0];
        const days = parseInt(args[1]) || 30;
        if (!user || !token) return message.channel.send("Usage: +ajoutbot @user TOKEN [jours]");

        const expiryDate = new Date(Date.now() + days*24*60*60*1000).toISOString().split('T')[0] + " 23:59:59";
        const botId = bots.length + 1;
        const folder = await createBotClient(token, expiryDate, botId);

        bots.push({
            id: botId,
            clientId: user.id,
            token,
            createdAt: new Date().toISOString(),
            expiresAt: expiryDate,
            folder,
            active: true
        });
        saveBots();

        const member = message.guild.members.cache.get(user.id);
        if (member) await giveClientRole(message.guild, member, botId);

        const embed = new EmbedBuilder()
            .setTitle(`🟢 Bot Client Créé | ID ${botId}`)
            .setDescription(`Expire le : ${expiryDate}`)
            .setColor(0x57f287);
        message.channel.send({ embeds: [embed] });
    }

    if (cmd === "+supprbot") {
        const botId = parseInt(args[0]);
        if (!botId) return message.channel.send("Usage: +supprbot ID");
        const killed = await removeBot(botId, message.guild);

        const embed = new EmbedBuilder()
            .setTitle(`❌ Bot Supprimé | ID ${botId}`)
            .setDescription(killed ? "Process tué" : "Dossier supprimé")
            .setColor(0xe74c3c);
        message.channel.send({ embeds: [embed] });
    }

    if (cmd === "+listebots") {
        if (!bots.length) return message.channel.send({ embeds: [new EmbedBuilder().setTitle("Aucun bot").setColor(0xe74c3c)] });
        let desc = "";
        bots.forEach(b => {
            const days = remainingDays(b.expiresAt);
            desc += `• ID ${b.id} - Client: <@${b.clientId}> - expire dans ${days} jours\n`;
        });
        const embed = new EmbedBuilder().setTitle("Liste des Bots Clients").setDescription(desc).setColor(0x3498db);
        message.channel.send({ embeds: [embed] });
    }
});

client.once('ready', () => console.log(`${client.user.tag} prêt`));
client.login("TON_TOKEN_BOT_GESTION");