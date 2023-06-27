import discord
from discord.ext import commands
import pandas as pd
import mysql.connector as mydb
import re


#設定が必要な情報
# 1.TOKEN
# 2.table
# 3.introdコマンドチャンネルID
# 4.ロールID(2種類)
# 5.ギルドid,通知チャンネルID,ログチャンネルID
# 6.DB接続設定
# 7.管理者のdiscordIDを挿入

intents = discord.Intents.all()

#Botクラスの定義
class Bot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.all()
        super().__init__(command_prefix=commands.when_mentioned_or('!'), intents=intents)

    async def on_ready(self):
        print('ログインしました')

#discord_bot インスタンスの作成
bot = Bot()

#各変数の設定
TOKEN = 'your-discord-bot-token'  # TOKENを貼り付け
table = "member" #Mysqlテーブル名
introid = 000000000 #案内用チャンネルのID
role_pre = 000000000 #削除対象のロールID
role_aft = 000000000 #アカウント認証後のロールID
guild_id = 000000000 #discordサーバーのID
notify_ch = 000000000 #通知を送信するチャンネルのID
logch_id = 000000000 #管理用ログチャンネルのID
administrator_id = 000000000 #管理者のdiscordID

#メールアドレス判断用正規表現
pattern = "^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$" #メールアドレス判断用正規表現
int_mes = "案内用メッセージ"
int_id = [000000000] #認証開始メッセージID

#ユーザーが困ったときにヘルプを呼ぶ機能
class notify(discord.ui.View):
    def __init__(self, ctx):
        super().__init__()
        self.value = ctx

    #押すと管理チャンネルに通知と押したユーザーの名前、IDが通知される
    @discord.ui.button(label='ヘルプを呼ぶ', style=discord.ButtonStyle.green)
    async def noti(self, interaction: discord.Interaction, button: discord.ui.Button):
        ch = bot.get_channel(notify_ch)
        id = interaction.user.id
        user = discord.utils.get(bot.users, id=id)
        await ch.send(f"{user.name}さん({id})が助けを読んでいます")
        await interaction.response.send_message(content="少々お待ちください。")

#認証登録
class st2(discord.ui.View):
    def __init__(self, ctx):
        super().__init__()
        self.value = ctx

    @discord.ui.button(label='OK', style=discord.ButtonStyle.green)
    async def confirm2OK(self, interaction: discord.Interaction, button: discord.ui.Button):
        con = mydb.connect(host="localhost",port="0000",user='user',password='password',db='databese_name')
        cur = con.cursor(buffered=True)
        guild = bot.get_guild(guild_id)
        id = interaction.user.id
        user = guild.get_member(id)
        cur.execute(f"SELECT * FROM {table} WHERE id=%s", (str(id),))
        memb = cur.fetchone()
        step = int(memb[5])
        if step == 2:
            real_name = self.value.content
            step = 3
            cur.execute(f'UPDATE {table} SET step=%s WHERE id=%s', (step, id))
            cur.execute(
                f'UPDATE {table} SET real_name=%s WHERE id=%s', (real_name, id))
            con.commit()
            await interaction.response.send_message("これで認証登録は終了です、お疲れ様でした！")
            #認証が完了したユーザーのロール削除&追加
            role_p = guild.get_role(role_pre)
            role_a = guild.get_role(role_aft)
            await user.remove_roles(role_p)
            await user.add_roles(role_a)
            await user.edit(nick=real_name)
        cur.close()
        con.close()

    @discord.ui.button(label='やり直し', style=discord.ButtonStyle.red)
    async def confirm2NG(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message(content="もう一度氏名を入力して下さい")

# ログイン確認
@bot.event
async def on_ready():
    print('ログインしました')

#認証開始用メッセージを案内
@bot.command()
@commands.has_permissions(administrator=True)
async def introd(ctx: commands.Context):
    await ctx.message.delete()
    introroom = bot.get_channel(introid)
    
    await introroom.send(f"{int_mes}")

# ユーザー参加時処理
@bot.event
async def on_member_join(member):
    # ロール割り当て
    con = mydb.connect(host="localhost",port="0000",user='username',password='password',db='database_name')
    cur = con.cursor()
    role = member.guild.get_role(role_pre)
    await member.add_roles(role)
    # データベース追加
    if member.nick == None:
        cur.execute(f"INSERT INTO {table} VALUES (%s, %s, %s,%s,%s,%s);",
                    (member.id, member.name, None, None, None, 0))
    else:
        cur.execute(f"INSERT INTO {table} VALUES (%s, %s, %s,%s,%s,%s);",
                    (member.id, member.name, member.nick, None, None, 0))
    con.commit()
    cur.close()
    con.close()
    print("ユーザーを追加しました")


# ユーザーリスト作成用コマンド
@bot.command()
@commands.has_permissions(administrator=True)
async def makedata(ctx):
    await ctx.message.delete()
    con = mydb.connect(host="localhost",port="0000",user='username',password='password',db='database_name')
    cur = con.cursor()
    author = ctx.author
    if ctx.author.id == administrator_id:
        if author.nick == None:
            cur.execute(f"INSERT INTO {table} VALUES (%s, %s, %s,%s,%s,%s);",
                        (author.id, author.name, None, None, None, 0))
        else:
            cur.execute(f"INSERT INTO {table} VALUES (%s, %s, %s,%s,%s,%s);",
                        (author.id, author.name, author.name, None, None, 0))
        con.commit()
        print("makedata done")
    cur.close()
    con.close()

#botからユーザーに直接DMを送信 !send ID 内容 で使用 
#助けを呼ぶボタンを押した人やなにか困っていそうな人にbotから直接対応するための機能
@bot.command()
@commands.has_permissions(administrator=True)
async def send(ctx):
    logch = bot.get_channel(logch_id)
    arr = ctx.message.content.split() #送信先部分とメッセージ部分を分割
    id = int(arr[1])
    content = arr[2]
    user = discord.utils.get(bot.users, id=id)
    await user.send(content)
    await logch.send(f"{user.name}({id})さんへ:{content}")

#送信者のデータをリセットする
@bot.command()
@commands.has_permissions()
async def reset(ctx):
    await ctx.message.delete()
    con = mydb.connect(host="localhost",port="0000",user='username',password='password',db='database_name')
    cur = con.cursor()
    id = ctx.author.id
    cur.execute(f"SELECT * FROM {table} WHERE id=%s", (str(id),))
    memb = cur.fetchone()
    step = memb[5]
    step = 0
    cur.execute(f'UPDATE {table} SET step=%s WHERE id=%s', (step, id))
    con.commit()
    cur.close()
    con.close()


@bot.event
async def on_message(ctx):
    if ctx.content == int_mes:
        int_id.append(ctx.id)
        print(f"{ctx.id}")
    if ctx.guild == None:
        if ctx.author.bot != True:
            logch = bot.get_channel(logch_id)
            content = ctx.content
            author = ctx.author
            name = author.display_name
            id = author.id
            await logch.send(name+f"({id})から: "+content)
    if ctx.guild == None:
        if ctx.author.bot == True:
            pass
        else:
            con = mydb.connect(host="localhost",port="0000",user='username',password='password',db='database_name')
            cur = con.cursor(buffered=True)
            id = ctx.author.id
            cur.execute(f"SELECT * FROM {table} WHERE id=%s", (str(id),))
            memb = cur.fetchone()
            step = int(memb[5])
            if step == 1:
                #メール認証
                if re.match(pattern, ctx.content):
                    sql= "select exists(select * from users where email=%s);"
                    email = (ctx.content,)
                    view = notify(ctx)
                    step = 2
                    try:
                        cur.execute(sql,email)
                    except mydb.Error as err:
                        raise
                    if cur.fetchone()[0]==0:
                        #emailが無い時
                        ###データ保存用サーバーの更新処理を行うプログラムを挿入してください###
                        try:
                            cur.execute(sql,email)
                        except mydb.Error as err:
                            raise
                        email = ctx.content
                        if cur.fetchone()[0]==0:
                            await ctx.channel.send("正しいメールアドレスを入力してください。\nうまくいかない場合はこちらのボタンを押してください。",view=view)
                        else:
                            cur.execute(f"SELECT * FROM {table} WHERE id=%s", (id,))
                            try:
                                cur.execute(f'UPDATE {table} SET step=%s WHERE id=%s', (step,id))
                                cur.execute(f'UPDATE {table} SET email=%s WHERE id=%s', (email, id))
                            except mydb.Error as err:
                                raise
                            try:
                                cur.execute(f'UPDATE {table} SET email=%s WHERE id=%s', (email, id))
                            except mydb.Error as err:
                                raise
                            con.commit()
                            await ctx.channel.send(content="メールアドレスの照合が完了しました！\n次に、あなたの氏名を入力してください！")
                    else:
                        email = ctx.content
                        cur.execute(f"SELECT * FROM {table} WHERE id=%s", (id,))
                        try:
                            cur.execute(f'UPDATE {table} SET step=%s WHERE id=%s', (step,id))
                            cur.execute(f'UPDATE {table} SET email=%s WHERE id=%s', (email, id))
                        except mydb.Error as err:
                            raise
                        try:
                            cur.execute(f'UPDATE {table} SET email=%s WHERE id=%s', (email, id))
                        except mydb.Error as err:
                            raise
                        con.commit()
                        await ctx.channel.send(content="メールアドレスの照合が完了しました！\n次に、あなたの氏名を入力してください！")
                else:
                    await ctx.channel.send("メールアドレスを入力してください。")
            elif step == 2:
                view = st2(ctx)
                await ctx.channel.send("入力内容はこれで間違いないですか？", view=view)
            cur.close()
            con.close()

    await bot.process_commands(ctx)

@bot.command()
async def stopmain(ctx):
    if ctx.author.id == administrator_id:
        await ctx.message.delete()
        await bot.close()

@bot.event
async def on_raw_reaction_add(ctx):
    view = notify(ctx)
    if ctx.message_id in int_id:
        con = mydb.connect(host="localhost",port="0000",user='username',password='password',db='database_name')
        cur = con.cursor(buffered=True)
        ch = bot.get_channel(notify_ch)
        id = ctx.user_id
        user = discord.utils.get(bot.users, id=id)
        cur.execute(f"SELECT * FROM {table} WHERE id=%s", (str(id),))
        memb = cur.fetchone()
        if memb != None:
            step = memb[5]
            if step == "0":
                step = 1
                cur.execute(
                    f'UPDATE {table} SET step=%s WHERE id=%s', (step, id))
                await user.send("これから認証登録を始めます！\n登録したメールアドレスを送信してください！")
                con.commit()
        else:
            await ch.send(f"{user.name}さん({id})のリストが作成されていません")
            cur.execute(f"INSERT INTO {table} VALUES (%s, %s, %s,%s,%s,%s);",
                        (user.id, user.name, user.display_name, None, None, 0))
            con.commit()
        cur.close()
        con.close()

#テスト用コマンド 以下はロール付与・削除の例
@bot.command()
@commands.has_permissions(administrator=True)
async def test(ctx):
    guild = bot.get_guild(guild_id)
    id = ctx.author.id
    user = guild.get_member(id)
    role_p = guild.get_role(role_pre)
    role_a = guild.get_role(role_aft)
    await user.remove_roles(role_p)
    await user.add_roles(role_a)

bot.run(TOKEN)