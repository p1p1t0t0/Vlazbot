const { Client, GatewayIntentBits, Partials, Collection, EmbedBuilder } = require('discord.js');
const TOKEN = "TOKENCLIENT"; // Ne pas toucher !!
const EXPIRY_DATE = "2099-12-31 23:59:59"; // Date d'expiration du bot

const client = new Client({
    intents: [
        GatewayIntentBits.Guilds,
        GatewayIntentBits.GuildMessages,
        GatewayIntentBits.MessageContent,
        GatewayIntentBits.GuildMembers
    ],
    partials: [Partials.Channel]
});

const statusCycle = ["En ligne", "Prêt à aider", "Prefix ?"];
let statusIndex = 0;

function isExpired() {
    return new Date() > new Date(EXPIRY_DATE);
}

client.once('ready', () => {
    console.log(`${client.user.tag} prêt | Expiration : ${EXPIRY_DATE}`);
    setInterval(changeStatus, 15000);
    setInterval(checkExpiry, 60000);
});

function changeStatus() {
    client.user.setActivity(statusCycle[statusIndex], { type: 0 });
    statusIndex = (statusIndex + 1) % statusCycle.length;
}

function checkExpiry() {
    if (isExpired()) {
        console.log(`${client.user.tag} expiré, déconnexion...`);
        client.destroy();
    }
}

client.on('messageCreate', async message => {
    if (!message.guild || message.author.bot) return;
    const args = message.content.trim().split(/ +/g);
    const cmd = args.shift().toLowerCase();

    if (cmd === "?ping") {
        message.channel.send(`Pong! ${client.ws.ping}ms`);
    }

    if (cmd === "?support") {
        message.channel.send("Pour toute aide, contacte le serveur support.");
    }

    if (cmd === "?help") {
        const embed = new EmbedBuilder()
            .setTitle("Commandes disponibles")
            .addFields(
                { name: "?ping", value: "Test du bot", inline: false },
                { name: "?support", value: "Lien du support", inline: false },
                { name: "?ban", value: "Bannir un membre", inline: false },
                { name: "?kick", value: "Expulser un membre", inline: false }
            )
            .setColor(0x3498db);
        message.channel.send({ embeds: [embed] });
    }

    if (cmd === "?ban") {
        const member = message.mentions.members.first();
        if (!member) return message.channel.send("Mentionne un membre à bannir.");
        try {
            await member.ban({ reason: args.join(" ") || "Aucune raison fournie" });
            message.channel.send(`${member.user.tag} a été banni.`);
        } catch {
            message.channel.send("Impossible de bannir ce membre.");
        }
    }

    if (cmd === "?kick") {
        const member = message.mentions.members.first();
        if (!member) return message.channel.send("Mentionne un membre à expulser.");
        try {
            await member.kick(args.join(" ") || "Aucune raison fournie");
            message.channel.send(`${member.user.tag} a été expulsé.`);
        } catch {
            message.channel.send("Impossible d'expulser ce membre.");
        }
    }
});

client.login(TOKEN);