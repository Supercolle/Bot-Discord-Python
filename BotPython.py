import discord
from discord.ext import commands
from discord.ui import View, Button
import random
from config import *

intents = discord.Intents.default()
intents.guilds = True
intents.members = True
intents.messages = True
intents.message_content = True  # necessario per leggere i messaggi DM

bot = commands.Bot(command_prefix="!", intents=intents)

# Dizionario per tracciare i ticket aperti {canale_id: user_id}
tickets = {}

# ---------------- CLOSE BUTTON ----------------
class TicketCloseView(View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Chiudi Ticket", style=discord.ButtonStyle.red, emoji="🔒")
    async def close_ticket(self, interaction: discord.Interaction, button: Button):
        channel = interaction.channel
        if channel.id not in tickets:
            await interaction.response.send_message("Questo canale non è un ticket.", ephemeral=True)
            return

        # Controllo permessi: staff o admin
        user_roles_ids = [r.id for r in interaction.user.roles]
        if STAFF_ROLE_ID not in user_roles_ids and not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("Solo lo staff può chiudere il ticket.", ephemeral=True)
            return

        user_id = tickets.pop(channel.id)
        user = await bot.fetch_user(user_id)

        # Log del ticket
        log_channel = interaction.guild.get_channel(LOG_CHANNEL_ID)
        if log_channel:
            embed = discord.Embed(title="📁 Ticket Chiuso", color=discord.Color.red())
            embed.add_field(name="Canale", value=channel.name)
            embed.add_field(name="Chiuso da", value=interaction.user.mention)
            embed.add_field(name="Autore", value="ANONIMO")
            await log_channel.send(embed=embed)

        await interaction.response.send_message("✅ Ticket chiuso.", ephemeral=True)
        await channel.delete()

# ---------------- DM HANDLER: CREA TICKET ----------------
@bot.event
async def on_message(message):
    # Processa comandi
    await bot.process_commands(message)

    if message.guild is None and not message.author.bot:  # Messaggio DM
        user = message.author
        content = message.content

        guild = bot.get_guild(GUILD_ID)
        category = guild.get_channel(TICKET_CATEGORY_ID)
        staff_role = guild.get_role(STAFF_ROLE_ID)

        if category is None:
            await message.channel.send("❌ Categoria ticket non trovata. Contatta un admin.")
            return
        if staff_role is None:
            await message.channel.send("❌ Ruolo staff non trovato. Contatta un admin.")
            return

        # Crea canale ticket
        ticket_id = random.randint(1000, 9999)
        channel_name = f"ticket-{ticket_id}"

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            guild.me: discord.PermissionOverwrite(view_channel=True),
            staff_role: discord.PermissionOverwrite(view_channel=True, send_messages=True)
        }

        channel = await guild.create_text_channel(
            name=channel_name,
            category=category,
            overwrites=overwrites
        )

        tickets[channel.id] = user.id

        # Invia il messaggio anonimo nello staff channel con bottone chiudi
        embed = discord.Embed(
            title=f"🎫 Nuovo Ticket #{ticket_id}",
            description=content,
            color=discord.Color.green()
        )
        await channel.send(embed=embed, view=TicketCloseView())
        await message.channel.send("✅ Ticket inviato correttamente, lo staff lo leggerà anonimamente.")

# ---------------- COMMAND: PANNELLO IN CANALE ----------------
@bot.command()
@commands.has_permissions(administrator=True)
async def ticketpanel(ctx):
    embed = discord.Embed(
        title="🎫 Sistema Ticket",
        description="Invia un DM al bot per aprire un ticket anonimo. Lo staff leggerà senza sapere chi ha scritto.",
        color=discord.Color.green()
    )
    await ctx.send(embed=embed)

bot.run(TOKEN)
