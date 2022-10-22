# 0608
# queue(list) 대기목록 제작
# skip 기능
# embed 사용해서 UI 제작
# 썸네일, 제목, queue
# 채널에 명령어 없이 노래제목 또는 가수 이름을 검색하면 제일 상단에 있는 노래 틀어주기

import youtube_dl
import discord
import asyncio
from bs4 import BeautifulSoup
import requests
import time
# pynacl

# 유튜브의 동적 웹페이지 기능 때문에 bs4로는 한계가 있다.
# 동적 웹페이지 처리를 위해 selenium 사용
#https://www.youtube.com/results?search_query=%EC%97%90%EC%8A%A4%ED%8C%8C
#https://www.youtube.com/results?search_query=에스파
from selenium import webdriver

client = discord.Client()

# 재생목록
play_list = []
# 스킵쓰이는 변수
music_skip = True

@client.event
async def on_ready():
    await client.change_presence(status=discord.Status.online, activity=discord.Game("Music")) # 봇 상태 표시줄
    #await client.login('OTYzNzQ1MzM1MTExNDU0NzUw.YlajyQ.K8c8AWzIrEjjcYGd1sJJR_ZCDfE')
    print('We have logged in as {0.user}'.format(client)) #로그인 되면 터미널에 출력

@client.event
async def on_message(message):
    global music_skip
    # 봇이 채팅 무시
    if message.author.bot :
        return
    if message.author == client.user:
        return
        
    # 뮤직 채널을 만들고 그 안에서 노래 제목이나 가수 이름으로 노래 가져오기
    if message.channel.name == "music":
        # !play [url] 
        if message.content.startswith("!play"):
            text = message.content.replace("!play ","")
            await store(message=message,url=text)
            return
        # !leave 채널 떠나기
        elif message.content.startswith("!leave"):
            await leave()
            await message.delete()
            return
        # !skip
        elif message.content.startswith("!skip"):
            music_skip = False
            await message.delete()
            return
        # 가수 이름이나 노래 제목을 입력하면 유튜브 제일 상단 영상 출력
        else:
            await __search(message)
            return
        
# 가수 이름이나 노래 제목을 입력하면 유튜브 제일 상단 영상 출력
async def __search(message):
    # 유튜브뮤직에서 노래 가져오기
    # 동적페이지는 bs4로 작업이 불가능해서 selenium 사용
    options = webdriver.ChromeOptions()
    options.add_argument("headless")
    options.add_argument('--window-size= 1600,900')
    driver = webdriver.Chrome('chromedriver', options=options)
    
    text = 'https://www.youtube.com/results?search_query=' + message.content
    driver.get(text)
    driver.implicitly_wait(1)
    
    # 가수를 검색하면 옆에 노래목록에서 노래 제목 추천
    # ㅁㅁㅁ 가수의 노래 xxx,xxx,xxx,xxx ...
    # 노래를 검색하면 첫 번째 영상 출력
    # 노래를 검색했을 때도 옆에 노래목록이 나오는 경우가 있음 ex) Savage
    # 에스파의 Savage를 듣고 싶어서 검색했지만  그룹 Savage의 info 나옴
    # 안내사항을 뒤에 붙혀서 가수 + 노래 로 검색하게 유도
    
    html = driver.page_source
    soup = BeautifulSoup(html, 'html.parser')
    
    meta = soup.find_all('ytd-watch-card-compact-video-renderer')
    # 노래목록이 있으면 노래추천
    if meta:
        tmp = message.content + '의 노래 추천목록\n'
        for data in meta:
            #test = data.find('a',{'class':"yt-simple-endpoint style-scope ytd-watch-card-compact-video-renderer"})
            #print(test['href'])
            test = data.find('yt-formatted-string','title')
            tmp =tmp + '-> ' + test.text + '\n'
        tmp += '```원하는 노래가 나오지 않으면 [가수 + 노래]로 입력해주세요.```'
        msg = await message.channel.send(tmp)
        time.sleep(5)
        await message.delete()
        await msg.delete()
        
    # 노래목록이 없으면 첫번째 영상 출력
    else:
        video = soup.find('a',id = 'video-title')
        url = "https://www.youtube.com"+video['href']
        print('href = '+ url)
        await store(message=message,url=url)
    
    driver.quit()

# 수정하는 내용은 큐 리스트
async def edit_embed(channel):
    global play_list
    # q = 플레이 리스트 출력문
    q = 'play list :'
    h_token = True
    
    if play_list:
        async for m in channel.history():
            # 메시지에 임베드가 있으면 갱신 update
            if m.embeds:
                for embed in m.embeds:
                    if "Music" in embed.title:
                        if play_list:
                            # 큐 리스트
                            for music in play_list:
                                q = q + '\n' + '-> ' + music[0]
                        # 메시지 수정
                        await m.edit(content = q)
                        h_token = False
                        return
        # 없으면 새로 만들기
        if h_token:
            embed = discord.Embed(title="Music",description='',color=0xFFFF00)
            embed.add_field(name="Now playing...",value=play_list[0][0],inline=False)
            await channel.send(embed = embed)
            return
    else:
        print("empty play list")
    
# 노래 저장하기
async def store(message,url):
    global music_skip
    # 채널 설정
    try:
        v_channel = message.author.voice.channel
    except:
        await message.channel.send("음성채널에 들어와주세요.")
    # 메세지를 보내기 위한 채널 설정
    t_channel = message.channel
    
    # 메세지 삭제
    await message.delete()
        
    # 이 봇이 속해있는 음성채널이 없다면 접속
    if client.voice_clients == []:
        await v_channel.connect()
    
    # 노래 제목 가져오기
    r = requests.get(url=url)
    if r.status_code == 200:
        html = r.text
        soup = BeautifulSoup(html, 'html.parser')
        title = soup.find("title")
        title = title.text.replace("- YouTube",'')
        play_list.append([title,url])
        
    # 노래 정보 출력
    await edit_embed(channel=t_channel)
    
    # 노래가 재생되고 있다면 넘어가고, 아니면 노래 재생하기
    if client.voice_clients[0].is_playing():
        pass
    else:
        await play(channel=t_channel)

async def play(channel):
    global music_skip
    # youtube_dl 옵션
    ydl_opts = {'format':'bestaudio'}
    FFMPEG_OPTIONS = {'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5', 'options': '-vn'}
    
    while True:
        if client.voice_clients[0].is_playing():
            if music_skip == False:
                voice.stop()
                music_skip = True
            await asyncio.sleep(0.1)
        else:
            if play_list:
                try:
                    # play_list 0번은 title, 1번은 url
                    music = play_list.pop(0)
                    # 영상 변환
                    with youtube_dl.YoutubeDL(ydl_opts) as ydl:
                        info = ydl.extract_info(music[1], download=False)
                        URL = info['formats'][0]['url']
                    # 노래 송출
                    voice = client.voice_clients[0]
                    voice.play(discord.FFmpegPCMAudio(URL,**FFMPEG_OPTIONS))
                    
                    async for m in channel.history():
                        # 메시지에 임베드가 있으면 갱신 update
                        if m.embeds:
                            for embed in m.embeds:
                                if "Music" in embed.title:
                                    newembed = discord.Embed(title="Music",description='',color=0xFFFF00)
                                    # 유튜브 영상 주소와 공유하기 주소가 다름
                                    # find는 찾는 문자의 위치를 반환
                                    # find의 결과가 없으면 -1 반환
                                    if music[1].find("v="):
                                        # https://www.youtube.com/watch?v=Jh4QFaPmdss
                                        idx = music[1].find("v=")
                                    else:
                                        # https://youtu.be/Jh4QFaPmdss
                                        idx = music[1].find("e/")
                                    # 썸네일 사진 가져오기
                                    img = "https://img.youtube.com/vi/"+music[1][idx+2:idx+13]+"/hqdefault.jpg"
                                    
                                    # 큐 리스트
                                    q = 'play list :'
                                    if play_list:
                                        for music in play_list:
                                            q = q + '\n' + '-> ' + music[0]
                                            
                                    newembed.set_image(url=img)
                                    newembed.add_field(name="Now playing...",value=music[0],inline=False)
                                    await m.edit(embed=newembed,content = q)
                
                except:
                    msg = await channel.send("잘못된 url 입니다.")
                    time.sleep(1)
                    del play_list[0]
                    await msg.delete()
            # 리스트가 비어있으면 퇴장
            else:
                await edit_embed(channel=channel)
                await leave()
                break
                
async def leave():
    # 음성채널 퇴장
    await client.voice_clients[0].disconnect()
    return

client.run('your token')
