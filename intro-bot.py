import discord
from discord.ext import commands
from discord.utils import get
import youtube_dl
import os
import random
from pydub import AudioSegment
from asgiref.sync import async_to_sync

TOKEN = os.getenv('DISCORD_TOKEN')
client = commands.Bot('!')

@client.event
async def on_voice_state_update(member, before, after):
    if before.channel and len(before.channel.members) == 1 and before.channel.members[0] == client.user:
        voice = get(client.voice_clients, guild=before.channel.guild)
        if len(voice.channel.members) == 1 and voice.channel.members[0] == client.user:
            if voice and voice.is_playing():
                voice.stop()
            if voice and voice.is_connected():
                await voice.disconnect()
    if before.channel and after.channel and len(before.channel.members) == len(after.channel.members):
        return 
    if member == client.user:
        return
    if after.channel:
        voice = get(client.voice_clients, guild=after.channel.guild)
        channel = after.channel 
        if voice and voice.is_connected():
            if channel != voice.channel:
                await voice.move_to(channel)
        else:
            voice = await channel.connect()
        if len(voice.channel.members) == 1 and voice.channel.members[0] == client.user:
            if voice and voice.is_playing():
                voice.stop()
            if voice and voice.is_connected():
                await voice.disconnect()
            
        if voice and voice.is_playing():
            voice.stop()
         
        songs, directory = getSongs(member)
        if songs:
            song = random.choice(songs)
            voice.play(discord.FFmpegPCMAudio(f"{directory}/{song}"), after=lambda e: exitChannel(voice))
            voice.source = discord.PCMVolumeTransformer(voice.source)
            voice.source.volume = 0.3
    
def getSongs(member):
    directory = f'./{member}' if os.path.isdir(os.path.join('./', str(member))) else './DefaultSongs'
    return [song for song in os.listdir(directory) if song.endswith('.mp3')], directory

@async_to_sync
async def exitChannel(voice):
    if voice and voice.is_connected() and not voice.is_playing():
        await voice.disconnect()

@client.command(pass_context=True, aliases=['j', 'joi'])
async def join(ctx):
    channel = ctx.message.author.voice.channel
    voice = get(client.voice_clients, guild=ctx.guild)

    if voice and voice.is_connected():
        await voice.move_to(channel)
    else:
        voice = await channel.connect()

    await voice.disconnect()

    if voice and voice.is_connected():
        await voice.move_to(channel)
    else:
        voice = await channel.connect()

    await ctx.send(f"Joined {channel}")

@client.command(pass_context=True, aliases=['l', 'lea'])
async def leave(ctx):
    channel = ctx.message.author.voice.channel
    voice = get(client.voice_clients, guild=ctx.guild)

    if voice and voice.is_connected():
        await voice.disconnect()
        await ctx.send(f"Left {channel}")
    else:
        await ctx.send("Don't think I am in a voice channel")

@client.command(pass_context=True)
async def myClips(ctx):
    member = ctx.message.author
    clips, directory = getSongs(member)
    for i in range(len(clips)):
        await ctx.send(f'{i+1}.) {clips[i]}')

@client.command(pass_context=True)
async def add(ctx, url:str, start:str=None, end:str=None):
    member = ctx.message.author
    ydl_opts = {
        'outtmpl': str(member)+'/'+'%(title)s.%(ext)s',
        'format': 'bestaudio/best',
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
    }
    try:
        with youtube_dl.YoutubeDL(ydl_opts) as ydl:
            title=ydl.extract_info(url, download=False)['title']
            ydl.download([url])
    except youtube_dl.utils.DownloadError as e:
        await ctx.send(f"Failure: Clip for {url} was not added because it is not a valid Youtube link")
        return 0
    try:
        song = AudioSegment.from_mp3(f"./{member}/{title}.mp3")
        song_length = song.duration_seconds * 1000
        ten_seconds = 10 * 1000
        clip_start = getMiliSeconds(start) if start else 0
        clip_end = getMiliSeconds(end) if end and start else clip_start + min(ten_seconds, song_length)
        if clip_end < clip_start or clip_end-clip_start > 20000 or clip_start > song_length or clip_end > song_length:
            raise NameError("Bad clip")
        cliped = song[clip_start:clip_end]
        cliped.export(f"./{member}/{title}{start}-{end}.mp3", format="mp3")
        await ctx.send(f"Successfully added {title} form {start}-{end} to {member}'s intro clips!")
    except (NameError, ValueError) as e:
        print(e)
        await ctx.send(f"Failure: Clip for {title} as not added because {start} and/or {end} were bad timestamps")
    os.remove(f'./{member}/{title}.mp3')

def getMiliSeconds(time):
    splits = list(reversed(time.split(':')))
    for i in splits:
        if len(i) >2:
            raise NameError("Bad split")
    seconds = sum([int(splits[i]) * (60**i) for i in range(len(splits))])
    return 1000*seconds

@client.command(pass_context=True)
async def delete(ctx, *, filename:str):
    member = ctx.message.author
    filename = filename.split('/')[-1]
    try:
        os.remove(f'./{member}/{filename}')
        await ctx.send(f"{filename} has been removed")
    except FileNotFoundError as e:
        await ctx.send(f"Failure: Unable to delete clip")

client.run(TOKEN)
