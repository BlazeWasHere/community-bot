import calendar
import datetime
import random

import discord
from discord import Embed
from discord.ext import commands, tasks
from discord.ext.commands import CommandOnCooldown

import tools


# Static function
async def GiveNewCard(UserInfo: list):
    NewCard = random.randint(1, 52)

    while NewCard in UserInfo[0]:
        NewCard = random.randint(1, 52)

    UserInfo[0].append(NewCard)

    return UserInfo


class Economy(commands.Cog):
    """Economy related commands"""

    def __init__(self, bot):
        self.bot = bot
        self.database = bot.database
        self.lottery.start()
        self.interest.start()
        self.executed = False
        self.interested = False
        self.owner_list = (553614184735047712, 148549003544494080, 518854761714417664)

        self.Storage = {}

        self.Names = {"1": "Ace", "11": "Jack", "12": "Queen", "0": "King"}
        self.Worth = {"11": 10, "12": 10, "0": 10, "1": 11}
        self.Types = ["Clubs", "Diamonds", "Hearts", "Spades"]
        self.Emotes = {self.Types[0]: ":clubs:", self.Types[1]: ":diamonds:", self.Types[2]: ":hearts:",
                       self.Types[3]: ":spades:"}

    @tasks.loop(seconds=60.0)
    async def lottery(self):
        db = self.database.bot
        posts = db.economy
        time = datetime.datetime.now()

        if time.hour == 4:
            self.executed = False
            return
        if self.executed:
            return
        if time.hour != 00 and time.minute not in [0,
                                                   2]:  # Prevent it running when it's not midnight and when it's not within the first few minutes of that hour
            return

        self.executed = True

        # Store the total tickets to get the amount that should be paid out
        total_daily, total_weekly, total_monthly = 0, 0, 0

        daily_winners, weekly_winners, monthly_winners = [], [], []

        async for user in posts.find({}):
            daily = user["d_lottery_tickets"]
            weekly = user["w_lottery_tickets"]
            monthly = user["m_lottery_tickets"]

            if daily > 0:
                total_daily += daily
                daily_winners.append(user["user_id"])
            elif weekly > 0:
                total_weekly += weekly
                weekly_winners.append(user["user_id"])
            elif monthly > 0:
                total_monthly += monthly
                monthly_winners.append(user["user_id"])

        total_daily_money = total_daily * 20
        total_weekly_money = total_weekly * 40
        total_monthly_money = total_monthly * 100

        end_daily_winners = None
        end_weekly_winners = []
        end_monthly_winners = []

        daily_money = total_daily * 20

        # The variable will first be assigned, then the check will be performed,
        # So the check would be useless if the else part divides by 0 and is part of the 'if' statement
        weekly_money = 0 if len(end_weekly_winners) == 0 else int((total_weekly * 40) / len(end_weekly_winners))
        monthly_money = 0 if len(end_monthly_winners) == 0 else int((total_monthly * 100) / len(end_monthly_winners))

        if len(daily_winners) > 4:  # Needs 4 or more players
            end_daily_winners = random.choice(daily_winners)
        if len(weekly_winners) > 8:  # Needs 8 or more players

            choice1 = random.choice(weekly_winners)
            choice2 = random.choice(weekly_winners)

            while choice2 == choice1:
                choice2 = random.choice(weekly_winners)

            end_weekly_winners.append(choice1)
            end_weekly_winners.append(choice2)

        if len(weekly_winners) > 12:  # Needs 12 or more players
            choice1 = random.choice(monthly_winners)
            choice2 = random.choice(monthly_winners)
            choice3 = random.choice(monthly_winners)
            while choice2 == choice1:
                choice2 = random.choice(monthly_winners)
            while choice3 == choice2 or choice3 == choice1:
                choice2 = random.choice(monthly_winners)

            end_monthly_winners.append(choice1)
            end_monthly_winners.append(choice2)
            end_monthly_winners.append(choice3)

        async for user in posts.find({}):
            daily = user["d_lottery_tickets"]
            weekly = user["w_lottery_tickets"]
            monthly = user["m_lottery_tickets"]

            if daily > 0 or weekly > 0 or monthly > 0:
                member = self.bot.get_user(user["user_id"])

                if end_daily_winners:  # Daily
                    if user["user_id"] == end_daily_winners:
                        end_balance = await self.add_balance(user["user_id"], daily_money)
                        embed = Embed(colour=0xac6f8f, description=f"You won the daily lottery!")
                        embed.add_field(name="Current balance:", value=f"{end_balance}", inline=False)
                        embed.add_field(name="Money earned:", value=f"{daily_money}", inline=False)
                        embed.set_footer(text="Ploxy | Lottery system")
                        await member.send(embed=embed)
                if time.weekday() + 1 == 7:
                    if end_daily_winners:
                        if user["user_id"] in end_weekly_winners:  # weekly
                            end_balance = await self.add_balance(user["user_id"], weekly_money)
                            embed = Embed(colour=0xac6f8f, description=f"You won the weekly lottery!")
                            embed.add_field(name="Current balance:", value=f"{end_balance}", inline=False)
                            embed.add_field(name="Money earned:", value=f"{weekly_money}", inline=False)
                            embed.set_footer(text="Ploxy | Lottery system")
                            await member.send(embed=embed)
                if calendar.monthrange(time.year, time.month)[1] == time.day:  # Monthly
                    if end_monthly_winners:
                        if user["user_id"] in end_monthly_winners:
                            end_balance = await self.add_balance(user["user_id"], monthly_money)
                            embed = Embed(colour=0xac6f8f, description=f"You won the monthly lottery!")
                            embed.add_field(name="Current balance:", value=f"{end_balance}", inline=False)
                            embed.add_field(name="Money earned:", value=f"{monthly_money}", inline=False)
                            embed.set_footer(text="Ploxy | Lottery system")
                            await member.send(embed=embed)

            await posts.update_one({"user_id": user["user_id"]},
                                   {"$set": {"d_lottery_tickets": 0, "w_lottery_tickets": 0, "m_lottery_tickets": 0}})

    @lottery.before_loop
    async def before_lottery(self):
        await self.bot.wait_until_ready()

    @tasks.loop(minutes=1.0)
    async def interest(self):
        db = self.database.bot
        posts = db.economy
        time = datetime.datetime.now()

        if time.hour == 4:
            self.interested = False
            return
        if self.interested:
            return
        if time.hour != 00 and time.minute not in [0,
                                                   2]:  # Prevent it running when it's not midnight and when it's not within the first few minutes of that hour
            return
        if calendar.monthrange(time.year, time.month)[1] != time.day:  # If not the end of the month
            return
        async for user in posts.find({}):
            balance = user["balance"]
            interest_money = balance * 0.05
            await self.add_balance(user["user_id"], interest_money)
        self.interested = True

    @interest.before_loop
    async def before_interest(self):
        await self.bot.wait_until_ready()

    async def add_money(self, user_id, guild_id, money):
        db = self.database.bot
        posts = db.economy
        user = await posts.find_one({"user_id": user_id})
        total_cash = user["cash"]
        total_cash[str(guild_id)] = total_cash[str(guild_id)] + money
        await posts.update_one({"user_id": user_id},
                               {"$set": {"cash": total_cash}})
        return total_cash[str(guild_id)]

    async def add_balance(self, user_id, money):
        db = self.database.bot
        posts = db.economy
        user = await posts.find_one({"user_id": user_id})
        money_total = money + user["balance"]
        await posts.update_one({"user_id": user_id},
                               {"$set": {"balance": money_total}})
        return money_total

    async def get_money(self, user_id, guild_id):
        db = self.database.bot
        posts = db.economy
        user = await posts.find_one({"user_id": user_id})
        return user["cash"][str(guild_id)]

    async def get_bank(self, user_id):
        db = self.database.bot
        posts = db.economy
        user = await posts.find_one({"user_id": user_id})
        return user["balance"]

    async def take_money(self, user_id, guild_id, money):
        db = self.database.bot
        posts = db.economy
        user = await posts.find_one({"user_id": user_id})
        total_cash = user["cash"]
        total_cash[str(guild_id)] = total_cash[str(guild_id)] - money
        await posts.update_one({"user_id": user_id},
                               {"$set": {f"cash": total_cash}})

        return total_cash[str(guild_id)]

    async def take_balance(self, user_id, money):
        db = self.database.bot
        posts = db.economy
        user = await posts.find_one({"user_id": user_id})
        money_total = user["balance"] - money
        await posts.update_one({"user_id": user_id},
                               {"$set": {"balance": money_total}})
        return money_total

    async def send_money(self, id1, id2, money):
        db = self.database.bot
        posts = db.economy

        user = await posts.find_one({"user_id": id1})

        money_total1 = user["balance"] - money

        await posts.update_one({"user_id": id1},
                               {"$set": {"balance": money_total1}})

        # receiver
        user = await posts.find_one({"user_id": id2})

        money_total2 = user["balance"] + money

        await posts.update_one({"user_id": id2},
                               {"$set": {"balance": money_total2, "user_id": id2}})

    @commands.group(name="economy", aliases=["eco"], usage="economy", no_pm=True)
    async def economy(self, ctx):
        pass

    @commands.command(name="beg", usage="beg", no_pm=True)
    @commands.cooldown(1, 1800, commands.BucketType.user)
    @tools.has_perm()
    async def beg(self, ctx):
        chance = random.randint(1, 100)
        if chance <= 40:
            amount = random.randint(10, 30)
            end_total = await self.add_money(ctx.author.id, ctx.guild.id, amount)
            embed = Embed(color=0x36a39f, title="You got paid!")
            embed.add_field(name="You earned", value=f"${amount}", inline=True)
            embed.add_field(name="Total Balance", value=f"${end_total}", inline=True)
            await ctx.send(embed=embed)
        else:
            choice = random.choice(["The rich were scared that 2008 will happen again, you didn't get anything.",
                                    "The rich found out you were a scammer! You didn't get anything.",
                                    "Money is scarce and you didn't get anything.",
                                    "Your partner stopped bothering to pay you anything.",
                                    "Your parents didn't send you money this month."])
            await ctx.send(choice)

    @beg.error
    async def on_beg_error(self, ctx, exception):
        error = getattr(exception, "original", exception)
        embed = discord.Embed(colour=0xac6f8f)
        if isinstance(error, CommandOnCooldown):
            seconds = error.retry_after
            timeVar = "minutes" if seconds > 120 else "seconds"
            timeLeft = round(seconds / 60, 1) if timeVar == "minutes" else round(seconds, 1)

            embed.add_field(name="You can't beg that soon",
                            value=f"You must wait {timeLeft} {timeVar} for the police to eat their doughnuts again.",
                            inline=False)

        embed.set_footer(text="Ploxy")
        await ctx.send(embed=embed)

    @commands.command(name="coinflip", usage="coinflip <head|tails> <bet>", no_pm=True)
    @tools.has_perm()
    async def coinflip(self, ctx, choice, bet: int):
        if await self.get_money(ctx.author.id, ctx.guild.id) < bet:
            return await ctx.send("Not enough money to buy this!")
        chance = random.choice(["Heads", "Tails"])
        if choice.lower() in ["head", "h", "heads"]:
            choice = "Heads"
        elif choice.lower() in ["tails", "t", "tail"]:
            choice = "Tails"
        else:
            return await ctx.send("That is not a valid option!")
        if choice == chance:
            end_total = await self.add_money(ctx.author.id, ctx.guild.id, bet)
            embed = Embed(color=0x36a39f, title="🪙 You chose right!")
            embed.add_field(name="You earned", value=f"${bet}", inline=True)
        else:
            end_total = await self.take_money(ctx.author.id, ctx.guild.id, bet)
            embed = Embed(color=0x36a39f, title="📉 You chose wrong!")
            embed.add_field(name="You lost", value=f"${bet}", inline=True)

        embed.add_field(name="Total Balance", value=f"${end_total}", inline=True)
        await ctx.send(embed=embed)

    @commands.group(invoke_without_command=True, case_sensitive=False, name="lottery", usage="lottery", no_pm=True)
    @tools.has_perm()
    async def lotterycmd(self, ctx):
        embed = Embed(color=0x36a39f, title="Lottery system")
        embed.add_field(name="Daily lottery",
                        value=f"\n$20 per ticket, chosen at midnight. Maximum 1 winner with 4 players.", inline=True)
        embed.add_field(name="Weekly lottery",
                        value=f"\n$40 per ticket, chosen at midnight on Saturday/Sunday. Maximum 2 winners with 8 players.",
                        inline=True)
        embed.add_field(name="Monthly lottery",
                        value=f"\n$100 per ticket, chosen at midnight on the last day of the month. Maximum 3 winners with 12 players.",
                        inline=True)
        embed.set_footer(text="Ploxy | Lottery system")
        await ctx.send(embed=embed)

    @lotterycmd.command(name="buy", aliases=["purchase", "own"], usage="lottery buy daily 100", no_pm=True)
    @tools.has_perm()
    async def lotterybuy(self, ctx, option, amount: int):
        embed = Embed(color=0x36a39f, title="Lottery system")
        total = 0
        if option.lower() == "daily":
            if await self.get_money(ctx.author.id, ctx.guild.id) < (amount * 20):
                return await ctx.send("Not enough money to buy this!")
            total = amount * 20
            embed.add_field(name="You bought", value=f"{amount} of daily tickets for ${total}", inline=True)
        elif option.lower() == "weekly":
            if await self.get_money(ctx.author.id, ctx.guild.id) < (amount * 40):
                return await ctx.send("Not enough money to buy this!")
            total = amount * 40
            embed.add_field(name="You bought", value=f"{amount} of weekly tickets for ${total}", inline=True)
        elif option.lower() == "monthly":
            if await self.get_money(ctx.author.id, ctx.guild.id) < (amount * 100):
                return await ctx.send("Not enough money to buy this!")
            total = amount * 100
            embed.add_field(name="You bought", value=f"{amount} of monthly tickets for ${total}", inline=True)
        else:
            return await ctx.send("We don't have that option for lottery")

        end_total = await self.take_money(ctx.author.id, ctx.guild.id, total)
        embed.add_field(name="Total Balance:", value=f"${end_total}", inline=True)
        embed.set_footer(text="Ploxy | Lottery system")
        await ctx.send(embed=embed)

    @commands.command(name="balance", aliases=["bal"], usage="bal", no_pm=True)
    @tools.has_perm()
    async def balance(self, ctx, user: discord.Member = None):
        if user is None:
            user = ctx.author

        db = self.database.bot
        posts = db.economy
        data = await posts.find_one({"user_id": user.id})

        embed = Embed(color=0x36a39f, title=f"Balance of {user.name}#{user.discriminator}")
        embed.add_field(name="💰Total Balance:", value=f"${data['balance']}", inline=True)
        embed.add_field(name="💸Total Cash:", value=f"${data['cash'][str(ctx.guild.id)]}", inline=True)
        embed.set_footer(text="Ploxy | Economy system")
        await ctx.send(embed=embed)

    @commands.command(name="pay", aliases=["transfer"], usage="pay @user money", no_pm=True)
    @tools.has_perm()
    async def pay(self, ctx, user: discord.Member, money: int):
        pre_balance = await self.get_bank(ctx.author.id)
        if pre_balance < money:
            return await ctx.send("Not enough bank balance to send this amount!")

        toSendId = user if type(user) is int else user.id

        if await self.database.bot.economy.count_documents({"user_id": toSendId}) == 0:
            return await ctx.send("Cannot pay the user !")

        await self.send_money(ctx.author.id, toSendId, money)

        db = self.database.bot
        posts = db.economy
        data = await posts.find_one({"user_id": ctx.author.id})

        embed = Embed(color=0x36a39f, title=f"Sent ${money} to {user.name}#{user.discriminator}", description=f"✅ {user.mention} has received the money!")
        embed.set_footer(text="Ploxy | Economy system")
        await ctx.send(embed=embed)

        data = await posts.find_one({"user_id": user.id})

        embed = Embed(color=0x36a39f, title=f"You got Money from {ctx.author.name}#{ctx.author.discriminator}!")
        embed.add_field(name="📧Money received:", value=f"${money}", inline=True)
        embed.add_field(name="💰Total Balance:", value=f"${data['balance']}", inline=True)
        embed.add_field(name="Link to channel:", value=f"{ctx.channel.mention}", inline=True)
        embed.set_footer(text=f"Ploxy | Economy system | {ctx.guild.name}")
        await user.send(embed=embed)

    @commands.command(name="deposit", aliases=["storemoney", "storecash", "dep"], usage="deposit <amount>", no_pm=True)
    @tools.has_perm()
    async def deposit(self, ctx, amount):
        db = self.database.bot
        posts = db.economy
        if amount[0] == "-" or amount == "0":
            return await ctx.send("Cannot withdraw amounts less than or equal to 0")
        if amount == "all":
            db_amount = await posts.find_one({"user_id": ctx.author.id})
            amount = db_amount['cash'][str(ctx.guild.id)]
        if await self.get_money(ctx.author.id, ctx.guild.id) < int(amount):
            return await ctx.send("Not enough cash to deposit this amount!")

        await self.take_money(ctx.author.id, ctx.guild.id, int(amount))
        await self.add_balance(ctx.author.id, int(amount))
        data = await posts.find_one({"user_id": ctx.author.id})
        embed = Embed(color=0x36a39f,
                      title=f"Deposited ${amount} in bank account of {ctx.author.name}#{ctx.author.discriminator}")
        embed.add_field(name="💰Total Balance:", value=f"${data['balance']}", inline=True)
        embed.add_field(name="💸Total Cash:", value=f"${data['cash'][str(ctx.guild.id)]}", inline=True)
        embed.set_footer(text="Ploxy | Economy system")
        await ctx.send(embed=embed)

    @commands.command(name="withdraw", aliases=["takemoney", "withdrawnmoney", "withdrawmoney", "with"],
                      usage="withdraw <amount>", no_pm=True)
    @tools.has_perm()
    async def withdraw(self, ctx, amount):
        if amount[0] == "-" or amount == "0":
            return await ctx.send("Cannot withdraw amounts less than or equal to 0")
        if amount == "all":
            amount = await self.get_bank(ctx.author.id)
        if await self.get_bank(ctx.author.id) < int(amount):
            return await ctx.send("Not enough cash to withdraw this amount!")

        db = self.database.bot
        posts = db.economy

        if amount == "all":
            amount = await posts.find_one({"user_id": ctx.author.id})['balance']

        await self.take_balance(ctx.author.id, int(amount))
        await self.add_money(ctx.author.id, ctx.guild.id, int(amount))
        data = await posts.find_one({"user_id": ctx.author.id})
        embed = Embed(color=0x36a39f,
                      title=f"Withdrawn ${amount} from bank account of {ctx.author.name}#{ctx.author.discriminator}")
        embed.add_field(name="💰Total Balance:", value=f"${data['balance']}", inline=True)
        embed.add_field(name="💸Total Cash:", value=f"${data['cash'][str(ctx.guild.id)]}", inline=True)
        embed.set_footer(text="Ploxy | Economy system")
        await ctx.send(embed=embed)

    @commands.command(name="work", usage="work")
    @commands.cooldown(1, 1800, commands.BucketType.user)
    @tools.has_perm()
    async def work(self, ctx):
        chance = random.randint(1, 100)

        if chance <= 70:
            amount = random.randint(1, 100)
            end_total = await self.add_money(ctx.author.id, ctx.guild.id, amount)
            embed = Embed(color=0x36a39f, title="You got paid!")
            embed.add_field(name="You earned", value=f"${amount}", inline=True)
            embed.add_field(name="Total Balance", value=f"${end_total}", inline=True)
            await ctx.send(embed=embed)
        else:
            choice = random.choice(["The dishes broke while you were washing them.", "Your boss caught you slacking!",
                                    "Stackoverflow brought the boss to your question, he wasn't happy."])
            await ctx.send(choice)

    @work.error
    async def on_work_error(self, ctx, exception):
        error = getattr(exception, "original", exception)
        embed = discord.Embed(colour=0xac6f8f)
        if isinstance(error, CommandOnCooldown):
            seconds = error.retry_after
            timeVar = "minutes" if seconds > 120 else "seconds"
            timeLeft = round(seconds / 60, 1) if timeVar == "minutes" else round(seconds, 1)
            message = ", the alarm still hasn't gone off yet." if timeVar == "minutes" else "seconds for the light to turn green."

            embed.add_field(name="You can't work that soon",
                            value=f"You must wait {timeLeft} {timeVar}{message}",
                            inline=False)

        embed.set_footer(text="Ploxy")
        await ctx.send(embed=embed)

    @commands.command(name="ecototalreset", usage="ecoreset")
    async def eco_total_reset(self, ctx):
        if ctx.author.id not in self.owner_list:
            return

        EcoPost = self.database.bot.economy
        await EcoPost.delete_many({})

        await ctx.send("The economy has successfully been reset")

    async def checkSum(self, Info):
        return sum(card % 13 if str(card % 13) not in self.Worth.keys() else self.Worth[str(card % 13)] for card in Info[0])

    async def addField(self, embed, Info, Name):
        fieldDescription = ", \u0020".join(
            f"{card % 13 if not str(card % 13) in self.Names else self.Names[str(card % 13)]} {self.Emotes[self.Types[card // 13]]}"
            for card in Info[0]
        )

        fieldDescription += f"\n\n**Score : {await self.checkSum(Info)}**"

        embed.add_field(name=f"**{Name}'s hand**", value=fieldDescription, inline=True)

        return embed

    async def displayBlackjackEmbed(self, message, UserInfo, HouseInfo, Status):
        if Status in ["won", "lost"]:
            BlackjackEmbed = discord.Embed(title="Blackjack", colour=3580831)
        else:
            BlackjackEmbed = discord.Embed(blackjack="\u200b", colour=3580831)

        BlackjackEmbed = await self.addField(BlackjackEmbed, UserInfo, message.author)
        BlackjackEmbed.add_field(name="\u200b", value="\u200b", inline=True)
        BlackjackEmbed = await self.addField(BlackjackEmbed, HouseInfo, "House")

        if Status in ["won", "lost"]:
            BlackjackEmbed.add_field(name="\u200b", value=f"**Outcome :** You {Status} {UserInfo[1]}", inline=False)
        else:
            BlackjackEmbed.add_field(name="\u200b", value=f"Options : **Draw** or **Stay**", inline=False)

        await message.channel.send(embed=BlackjackEmbed)

    async def BlackjackGather(self, UserId: str, Bet: int = 0):
        if UserId in self.Storage.keys():
            Cards = self.Storage[UserId]["Cards"]
            Bet = self.Storage[UserId]["Bet"]
        else:
            Cards = []
            Bet = Bet

        return [Cards, Bet]

    @commands.command(name="blackjack", usage="blackjack <amount>", aliases=["bj"])
    @tools.has_perm()
    async def blackjack(self, ctx, amount):
        if amount[0] == "-" or amount == "0":
            return await ctx.send("Cannot bet amounts less than or equal to 0")

        try:
            amount = int(amount)
        except ValueError:
            return await ctx.channel.send("A valid amount must be specified")

        if await self.get_money(ctx.author.id, ctx.guild.id) < amount:
            return await ctx.channel.send("Not enough money to bet that much")

        if str(ctx.author.id) not in self.Storage.keys():
            await self.take_money(ctx.author.id, ctx.guild.id, amount)
            User = await self.BlackjackGather(str(ctx.author.id), amount)
            House = await self.BlackjackGather(str(ctx.author.id) + "H", amount)

            User = await GiveNewCard(User)
            House = await GiveNewCard(House)

            await self.displayBlackjackEmbed(ctx, User, House, "")

            self.Storage[str(ctx.author.id)] = {"Cards": User[0], "Bet": amount}

            self.Storage[str(ctx.author.id) + "H"] = {"Cards": House[0], "Bet": amount}
        else:
            await ctx.channel.send("You already have a game of blackjack in progress")

    async def BlackjackAnswersHandler(self, message):
        End = False
        if message.content.lower() in ["d", "draw"] and str(message.author.id) in self.Storage.keys():
            User = await self.BlackjackGather(str(message.author.id))
            House = await self.BlackjackGather(str(message.author.id) + "H")

            User = await GiveNewCard(User)

            if await self.checkSum(User) > 21:
                await self.displayBlackjackEmbed(message, User, House, "lost")
                End = True

            elif await self.checkSum(User) == 21:
                await self.add_money(message.author.id, message.guild.id, int(User[1]) * 2)
                await self.displayBlackjackEmbed(message, User, House, "won")
                End = True

            else:
                self.Storage[str(message.author.id)]["Cards"] = User[0]

                await self.displayBlackjackEmbed(message, User, House, "")

        elif message.content.lower() in ["s", "stay"] and str(message.author.id) in self.Storage.keys():
            User = await self.BlackjackGather(str(message.author.id))
            House = await self.BlackjackGather(str(message.author.id) + "H")

            while not await self.checkSum(House) >= 17:
                House = await GiveNewCard(House)

            if await self.checkSum(House) > 21 or (await self.checkSum(User) > await self.checkSum(House)):
                await self.add_money(message.author.id, message.guild.id, int(User[1]) * 2)
                await self.displayBlackjackEmbed(message, User, House, "won")
                End = True

            elif await self.checkSum(House) == 21 or (await self.checkSum(User) <= await self.checkSum(House)):
                await self.displayBlackjackEmbed(message, User, House, "lost")
                End = True

        if End:
            del self.Storage[str(message.author.id)]
            del self.Storage[str(message.author.id) + "H"]

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.guild is None:
            return
        if message.author.bot:
            return

        if message.content.lower().split(" ")[0] in ["d", "draw", "s", "stay"]:
            await self.BlackjackAnswersHandler(message)


def setup(bot):
    bot.add_cog(Economy(bot))
