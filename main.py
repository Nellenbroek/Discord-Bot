import asyncio
import aiosqlite
import discord
import json
import requests
from discord.ext.commands import MissingPermissions
from discord.ext.commands import check
import random
import datetime
from discord.ext import commands, menus
from discord.ext.menus import MenuPages, ListPageSource
from discord import ui
from discord import Button, ButtonStyle, InteractionType
from osrsbox import monsters_api
import os
import sys


bot = commands.Bot(command_prefix='.', intents=discord.Intents.all())
bot.remove_command('help')
TOKEN = 'TOKEN HERE'
ADMINS = 355026064948592651, 520151823898771456, 449157382883246080, 981581698372362281
# Admins = Panchie,           Semperfi,           Masuro,             Exo Returns 
ADMINS_PTS = 355026064948592651, 520151823898771456, 449157382883246080, 981581698372362281
# Admins =    Panchie,            Semperfi,           Masuro,             Exo Returns,      
monsters = monsters_api.load() 
printed_monsters = set()
correct_guesses = {}
conn = None

@bot.event
async def on_ready():
    global conn
    print(f'{bot.user} is now online!')
    await bot.change_presence(activity=discord.Game(name=".help - Art clan"))
    bot.db = await aiosqlite.connect("bank.db")
    conn = await aiosqlite.connect('guess_leaderboard.db')
    await asyncio.sleep(3)
    async with bot.db.cursor() as cursor:
        # await cursor.execute('''CREATE TABLE IF NOT EXISTS bank (wallet INTEGER, bank INTEGER, maxbank INTEGER, user INTEGER)''')
        await cursor.execute('''CREATE TABLE IF NOT EXISTS leaderboard (points INTEGER, user INTEGER)''')
        await conn.execute('''CREATE TABLE IF NOT EXISTS guess_leaderboard (user_id TEXT PRIMARY KEY, points INTEGER DEFAULT 0)''')
    await bot.db.commit()
    await conn.commit()
    print("Database is ready!")


@bot.event
async def on_member_join(user):
    # await create_user_points(user)
    return print(f"{user.name} joined the server! (ID: {user.id})")


@bot.event
async def on_message(message):
    if message.author.bot:
        return
    author = message.author
    async with bot.db.cursor() as cursor:
        await bot.db.commit() 
        await bot.process_commands(message)


@bot.event
async def on_member_remove(user):
    await get_points(user) 
    async with bot.db.cursor() as cursor:
        await cursor.execute('''DELETE FROM leaderboard WHERE points AND user = ?''', (user.id,))
        await cursor.execute('''DELETE FROM leaderboard WHERE points = ? AND user = ?''', (0, user.id,))
        print(f"Removed {user} from the database (ID: {user.id})")
    await bot.db.commit()
    return


async def create_user_points(user):
    async with bot.db.cursor() as cursor:
        await cursor.execute('''INSERT INTO leaderboard VALUES(?, ?)''', (0, user.id,))
        print(f"Added {user.display_name} to the database (DISCORD_NAME: {user}, ID: {user.id})")
    await bot.db.commit()
    return


async def get_points(user):
    async with bot.db.cursor() as cursor:
        await cursor.execute('''SELECT points FROM leaderboard WHERE user = ?''', (user.id,))
        data = await cursor.fetchone()
        if data is None:
            await create_user_points(user)
            return await get_points(user)
        total_points = data[0]
        return total_points


async def update_points(user, amount: int):
    async with bot.db.cursor() as cursor:
        await cursor.execute('''SELECT points FROM leaderboard WHERE user = ?''', (user.id,))
        data = await cursor.fetchone()
        if data is None:
            await create_user_points(user)
            return await get_points(user)
        await cursor.execute('''UPDATE leaderboard SET points = ? WHERE user = ?''', (data[0] + amount, user.id))
    await bot.db.commit()


@bot.command()
async def check_users(ctx):
    user = ctx.author
    if user.id in ADMINS:
        guild = ctx.guild
        member_ids = [member.id for member in guild.members]
        
        async with bot.db.cursor() as cursor:
            await cursor.execute('''SELECT user FROM leaderboard''')
            result = await cursor.fetchall()
        
        missing_users = []
        for user_id in result:
            if user_id[0] not in member_ids:
                missing_users.append(user_id[0])
        
        if missing_users:
            missing_user_names = []
            for user_id in missing_users:
                user = await bot.fetch_user(user_id)
                missing_user_names.append(user.name)
            
            missing_users_str = ", ".join(missing_user_names)
            await ctx.send(f"The following users are missing from the server: {missing_users_str} (ID: {user_id})")
            async with bot.db.cursor() as cursor:
                await cursor.execute('''DELETE FROM leaderboard WHERE points AND user = ?''', (user_id,))
                await cursor.execute('''DELETE FROM leaderboard WHERE points = ? AND user = ?''', (0, user_id,))
            await ctx.send(f"{missing_users_str} has been successfully removed from the database")
            print(f"Removed {missing_users_names} from the database")
            await bot.db.commit()
        else:
            await ctx.send("All users are still in the server.")
    else:
        return await ctx.send("Missing role: __Administrator__")


class LeaderboardSource(menus.ListPageSource):
    def __init__(self, data):
        super().__init__(data, per_page=25)

    async def format_page(self, menu, entries):
        offset = menu.current_page * self.per_page
        em = discord.Embed(title="__Leaderboard__", color=discord.Color.random())
        for idx, (points, user_id) in enumerate(entries, start=offset):
            user = menu.ctx.guild.get_member(user_id)
            # em.add_field(name=f"{idx+1}) __{user.display_name}__ - {points} __points__", value="\n", inline=False)
            if points < 30 and points >= 0:
                em.add_field(name="", value=f"{idx+1}) <:emerald:1113260113860497428> **{user.display_name}** - **{points}** points" , inline=False)
            elif points < 100 and points >= 30:
                em.add_field(name="", value=f"{idx+1}) <:ruby:1113260127072563321> **{user.display_name}** - **{points}** points" , inline=False)
            elif points >= 100 and points < 250:
                em.add_field(name="", value=f"{idx+1}) <:diamond:1113260144206303323> **{user.display_name}** - **{points}** points", inline=False)
            elif points >= 250 and points < 500:
                em.add_field(name="", value=f"{idx+1}) <:dragonstone:1113260175772635137> **{user.display_name}** - **{points}** points" , inline=False)
            elif points >= 500 and points < 750:
                em.add_field(name="", value=f"{idx+1}) <:onyx:1113260204625240094> **{user.display_name}** - **{points}** points" , inline=False)
            elif points >= 750 and points < 1500:
                em.add_field(name="", value=f"{idx+1}) <:zenyte:1113260194248540300> **{user.display_name}** - **{points}** points" , inline=False)
            elif points >= 1500 and points < 2000:
                em.add_field(name="", value=f"{idx+1}) <:achiever:1113534230237024428> **{user.display_name}** - **{points}** points" , inline=False)
            elif points >= 2000 and points < 3000:
                em.add_field(name="", value=f"{idx+1}) <:completionist:1113534254673039364> **{user.display_name}** - **{points}** points" , inline=False)
            elif points >= 3000:
                em.add_field(name="", value=f"{idx+1}) <:elite:1113533237390749879> **{user.display_name}** - **{points}** points" , inline=False)
            em.set_footer(text="Tip: If the pagination buttons disappear or stop working,\nplease run the .leaderboard command again.")
        return em


@bot.command()
async def leaderboard(ctx):
    async with aiosqlite.connect("bank.db") as conn:
        cursor = await conn.execute('''SELECT points, user FROM leaderboard ORDER BY points DESC''')
        data = await cursor.fetchall()

    if data:
        source = LeaderboardSource(data)
        menu = menus.MenuPages(source=source, clear_reactions_after=True, timeout=60, check_embeds=True)
        await menu.start(ctx)
    else:
        await ctx.send("No users in database")

    
@bot.command(name="drop_leaderboard", help="Drops leaderboard (Hokus only)")
async def drop_leaderboard(ctx):
    user = ctx.author
    if user.id == 355026064948592651:
        async with bot.db.cursor() as cursor:
            await cursor.execute('''DROP TABLE leaderboard''')
            data = await cursor.fetchall()
            return await ctx.send("All users have been reset")
    else:
        print(f"{member.display_name} tried to use drop_leaderboard command")
        return await ctx.send("Missing role: __Administrator__")


@bot.command(name="remove_user", help="Removes a user from the database (Hokus only)")
async def remove_user(ctx, member: discord.Member):
    user = ctx.author
    if user.id == 355026064948592651:
            async with bot.db.cursor() as cursor:
                await cursor.execute('''DELETE FROM leaderboard WHERE points AND user = ?''', (member.id,))
                await cursor.execute('''DELETE FROM leaderboard WHERE points = ? AND user = ?''', (0, member.id,))
                print(f"Removed {member.display_name} from the database")
            await bot.db.commit()
            return await ctx.send(f"Successfully removed {member.display_name} from the database")
    else:
        print(f"{member.display_name} tried to use remove_user command")
        return await ctx.send("Missing role: __Administrator__")


@bot.command(name="points", help="Displays the points of a member - <name>")
async def points(ctx, member: discord.Member = None):
    if not member:
        member = ctx.author

    total_points = await get_points(member)  
    em = discord.Embed(color=discord.Color.random())
    em.set_author(name=f"{member.display_name}", icon_url=member.display_avatar)
    em.add_field(name="Points", value=total_points)
    return await ctx.send(embed=em)


@bot.command(name="add", help="Adds points to a member (admin only) - <name> <amount>")
async def add(ctx, member: discord.Member, amount):
    user = ctx.author
    if user.id in ADMINS_PTS:
        try:
            amount = int(amount)
        except ValueError:
            pass
        if type(amount) != int:
            em = discord.Embed(title=f"Adding point(s) to member failed", description=f"__You can only add integers to members!__")
            return await ctx.send(embed=em)
        elif amount < 0:
            return await ctx.send("Can't add negative numbers to players")
        else:
            amount = int(amount)
        await get_points(member)
        await update_points(member, amount)
        return await ctx.send(f"Added {amount} points to {member.display_name}")
    else:
        print(f"{member.display_name} tried to use Add command")
        return await ctx.send("Missing role: __Administrator__")


@bot.command(name="remove", help="Removes points from a member (admin only) - <name> <amount>")
async def remove(ctx, member: discord.Member, amount):
    user = ctx.author
    if user.id in ADMINS_PTS:
        try:
            amount = int(amount)
        except ValueError:
            pass
        if type(amount) != int:
            em = discord.Embed(title=f"Removing point(s) from member failed", description=f"__You can only remove integers from members!__")
            return await ctx.send(embed=em)
        elif amount < 0:
            return await ctx.send("Can't remove negative numbers from players")
        else:
            amount = int(amount)
        await update_points(member, -amount)
        await get_points(member)
        return await ctx.send(f"Removed {amount} points from {member.display_name}")
    else:
        print(f"{member.display_name} tried to use Remove command")
        return await ctx.send("Missing role: __Administrator__")


@bot.command()
async def help(ctx):
    embed = discord.Embed(
        title="Commands",
        color=discord.Color.random()
    )
    embed.add_field(name="Leaderboard", value="Shows the leaderboard of the clan.", inline=True)
    embed.add_field(name="Inspire", value="Returns a random famous quote to inspire you.", inline=True)
    embed.add_field(name="Roll", value="Rolls a random number between two values.", inline=True)
    embed.add_field(name="Guess", value="Returns a random image of an NPC that the player has to guess.", inline=True)
    embed.add_field(name="Guess_lb", value="Shows the leaderboard of the guessing game.", inline=True)
    await ctx.send(embed=embed)


@bot.command()
async def help_admin(ctx):
    user = ctx.author
    if user.id in ADMINS:
        embed = discord.Embed(
            title="Commands",
            color=discord.Color.random()
        )
        embed.add_field(name="Add", value="Adds points to a member. (e.g. .add Hokus 100)", inline=True)
        embed.add_field(name="Remove", value="Removes points from a member. (e.g. .remove Hokus 100)", inline=True)
        embed.add_field(name="Clear", value="Clears messages from a channel. (e.g. .clear 5)", inline=True)
        embed.add_field(name="Check_users", value="Checks if all the users in the leaderboard are also in the database.", inline=True)
        await ctx.send(embed=embed)
    else:
        return await ctx.send("Missing role: __Administrator__")


@bot.command(name="inspire", help="Returns a random famous quote to inspire you")
async def inspire(ctx):

    # Requests a quote from URL & loads it from json file
    response = requests.get('https://zenquotes.io/api/random')
    json_data = json.loads(response.text)

    # Sets the quote values
    quote = json_data[0]['q']
    inspiring_quote = '“' + quote + '”'
    quote_author = json_data[0]['a']
    inspiring_author = "- " + quote_author

    # Outputs the quote
    em = discord.Embed(description=inspiring_author, color=discord.Color.random(), title=inspiring_quote)
    await ctx.channel.send(embed=em)


@bot.command(name="roll", help="Rolls a random number between two values - <first_number> <second_number>")
async def roll(ctx, first_num: int, second_num: int):

    # Rolls a random number between first user input and second user input
    number = random.randint(int(first_num), int(second_num))

    # Outputs the user inputs and the random number chosen
    em = discord.Embed(color=discord.Color.random(), title=f"{ctx.author.display_name} rolls {number} ({first_num} - {second_num})")
    await ctx.channel.send(embed=em)


@bot.command(name="rollboss", help="Rolls a boss for Masuro to camp")
async def rollboss(ctx):
    bosses = ["50x Chaos Elemental", "50x Corrupted Gauntlet", "50x Giant Mole", "50x Sarachnis", "100x Chompy", "50x Wintertodt", "50x Kalphite Queen"]

    em = discord.Embed(color=discord.Color.random(), title=f"De boss die je gerold hebt is: ", description=f"{random.choice(bosses)}")
    await ctx.channel.send(embed=em)


@bot.command(name="clear", help="Clears messages from the channel - <amount>")
async def clear(ctx, amount):
    user = ctx.author
    if user.id in ADMINS:
        print(f"{ctx.author.display_name} cleared {amount} message(s)")
        return await ctx.channel.purge(limit=int(amount) + 1)
    else:
        return await ctx.send("Missing role: __Administrator__")


@bot.command()
async def guess(ctx):

    message_to_edit = None
    correct_guess_author = None
    # Finds the missing images
    # missing_images = []

    for monster in monsters:
        if monster.name not in printed_monsters:
            printed_monsters.add(monster.name)
            # print(monster.name)
    #         monster_name = monster.name.lower().replace(' ', '_')
    #         matching_images = [filename for filename in os.listdir('images') if monster_name in filename.lower()]
    #         if not matching_images:
    #             missing_images.append(monster.name)

    # if missing_images:
    #     print("Missing images:")
    #     for monster_name in missing_images:
    #         print(monster_name)
    # else:
    #     print("All images found!")


    # secret_monster = 'Woman'
    secret_monster = random.choice(list(printed_monsters))
    words = secret_monster.split()
    # hint = "   ".join(word[0] + " _" * (len(word) - 1) for word in words)
    # hint = "   ".join(word[:5] + " _" * (len(word) - 5) for word in words)
    hint = "   ".join(get_random_characters(word) for word in words)
    message_to_edit = await ctx.send(f"``{hint}``")
    # await ctx.send(f"``{hint}``")
    secret_monster = secret_monster.replace(" ", "_")


    matching_images = [filename for filename in os.listdir('images') if secret_monster.lower() in filename.lower()]
    if matching_images:
        image_path = os.path.join('images', matching_images[0])  # Choose the first element from the list
        with open(image_path, 'rb') as file:
            image = discord.File(file)
            await ctx.send(file=image)
    else:
        await ctx.send("Image not found.")

    def check(message):
        return not message.author.bot and message.channel == ctx.channel

    while True:
        try:
            secret_monster = secret_monster.replace("_", " ")
            guess_message = await asyncio.wait_for(ctx.bot.wait_for('message', check=check), timeout=20)
        except asyncio.TimeoutError:
            secret_monster = secret_monster.replace("_", " ")
            revealed_chars = [i for i, word in enumerate(secret_monster.split()) if word != "_"]
            revealed_word = " ".join(word if i in revealed_chars else "_" for i, word in enumerate(secret_monster.split()))
            revealed_word_with_spacing = " ".join(revealed_word)
            await message_to_edit.edit(content=f"``{revealed_word_with_spacing}``")
            await ctx.send(f"Too long since last guess. The npc was ``{secret_monster}``")
            return

        guess = guess_message.content.strip().lower()
        if guess == secret_monster.lower() or guess == secret_monster:
            correct_guess_author = guess_message.author.display_name
            if correct_guess_author in correct_guesses:
                points_gained = len(secret_monster)
                correct_guesses[correct_guess_author] += points_gained
            else:
                points_gained = len(secret_monster)
                correct_guesses[correct_guess_author] = points_gained


            # Update the leaderboard in the database
            async with conn.execute(''' INSERT OR REPLACE INTO guess_leaderboard (user_id, points) VALUES (?, COALESCE((SELECT points FROM guess_leaderboard WHERE user_id = ?), 0) + ?) ''', (correct_guess_author, correct_guess_author, points_gained)):
                await conn.commit()

            break

    if correct_guess_author:
        revealed_chars = [i for i, word in enumerate(secret_monster.split()) if word != "_"]
        revealed_word = " ".join(word if i in revealed_chars else "_" for i, word in enumerate(secret_monster.split()))
        revealed_word_with_spacing = " ".join(revealed_word)
        await message_to_edit.edit(content=f"``{revealed_word_with_spacing}``")
        await ctx.send(f"{correct_guess_author} got it right and gained {points_gained} points!")
        # await ctx.send(f"Total correct guesses for {correct_guess_author}: {correct_guesses[correct_guess_author]}")

def get_random_characters(word):
    num_chars = max(1, len(word) // 2)
    if len(word) <= 2:
        num_chars = random.choice([0, 1])
    revealed_chars = random.sample(range(len(word)), num_chars)
    hint = " ".join(word[i] if i in revealed_chars else "_" for i in range(len(word)))
    return hint


@bot.command()
async def guess_lb(ctx):
    # Retrieve the leaderboard from the database
    async with conn.execute(''' SELECT user_id, points FROM guess_leaderboard ORDER BY points DESC LIMIT 10''') as cursor:
        leaderboard_data = await cursor.fetchall()

    if leaderboard_data:
        embed = discord.Embed(title="Guessing Game Leaderboard", color=discord.Color.random())

        for position, (user_id, points) in enumerate(leaderboard_data, start=1):
            embed.add_field(name=f"Rank {position}: {user_id}", value=f"{points} points", inline=False)

        await ctx.send(embed=embed)
    else:
        await ctx.send("No data found in the leaderboard.")


@bot.event
async def on_bot_disconnect():
    await conn.close()
    await bot.db.close()


bot.run(TOKEN)