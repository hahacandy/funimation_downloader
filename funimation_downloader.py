from webdriver_manager.chrome import ChromeDriverManager
from selenium import webdriver
from selenium.webdriver.common.by import By
import time
import os
import requests
import threading
import re
from vtt_to_srt.vtt_to_srt import vtt_to_srt



def driver_set():
    option = webdriver.ChromeOptions()

    option.add_argument('--start-maximized')
    option.add_argument("disable-gpu")
    option.add_argument("user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_12_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/61.0.3163.100 Safari/537.36")
    option.add_argument("lang=ko_KR") # 한국어!

    driver = webdriver.Chrome(ChromeDriverManager().install(), options=option)
    return driver

def createFolder(directory):
    try:
        if not os.path.exists(directory):
            os.makedirs(directory)
    except OSError:
        print ('Error: Creating directory. ' +  directory)

def download(url, file_name):
    with open(file_name, "wb") as file:   # open in binary mode
        response = requests.get(url)               # get request
        file.write(response.content)      # write to file



def download_funimation_anime(driver, anime_url, save_path):
    

    driver.implicitly_wait(5)
    
    season_name = driver.find_element(By.XPATH, '//*[@id="main-content"]/div/div/div/div/div/div/div[2]/div/div/div/div/section[1]/div/div[1]/div/div[1]/div[1]/div[1]/div').text
    anime_name = driver.find_element(By.XPATH, '//*[@id="main-content"]/div/div/div/div/section/div/div[3]/article/div/div/div[2]/div/div[1]/h1').text
    
    anime_name = anime_name + '(' + season_name + ')'
    
    #ファイルをセーブするときエラーを避けるため
    season_name = re.sub(r'[\\/:*?"<>|]', '', season_name)
    anime_name = re.sub(r'[\\/:*?"<>|]', '', anime_name)

    thumbnail_url = driver.find_element(By.XPATH, '//*[@id="main-content"]/div/div/div/div/section/div/div[3]/article/div/div/div[1]/div[1]/div[2]')
    thumbnail_url = thumbnail_url.get_attribute('style')[thumbnail_url.get_attribute('style').find('url("') + 5:thumbnail_url.get_attribute('style').find('jpg")') + 3]
    
    createFolder(save_path + anime_name)
    download(thumbnail_url, save_path + anime_name + '/cover.jpg')

    anime_episodes_els = driver.find_element(By.XPATH, '//*[@id="main-content"]/div/div/div/div/div/div/div[2]/div/div/div/div/section[2]')

    anime_episodes_els = anime_episodes_els.find_elements(By.TAG_NAME, 'article')

    anime_episodes = []
    
    thread_list = []
    
    
    #アニメのリストのエレメントを抽出
    for anime_episodes_el in anime_episodes_els:
        anime_episode_info = {}
        anime_episode_info['name'] = anime_episodes_el.find_element(By.CLASS_NAME, 'v-card__title').text
        anime_episode_info['url'] = anime_episodes_el.find_element(By.TAG_NAME, 'a').get_attribute('href')

        anime_episodes.append(anime_episode_info)
        
    #字幕（vtt）とm3u8を得てアニメをダウンロードする
    for idx, anime_episode in enumerate(anime_episodes):
        vtt_url = None
        m3u8_url = None

        idx = idx + 1
        
        
        if idx < 10:
            idx= '00' + str(idx)
        elif idx <100:
            idx= '0' + str(idx)

        is_break = False

        while is_break == False:

            driver.get(anime_episode['url'])
            driver.implicitly_wait(5)

            try_idx = 1

            while try_idx < 5:

                try_idx = try_idx + 1

                JS_get_network_requests = "var performance = window.performance || window.msPerformance || window.webkitPerformance || {}; var network = performance.getEntries() || {}; return network;"
                network_requests = driver.execute_script(JS_get_network_requests)
                referer = network_requests[0]['name']

                for n in network_requests:
                    if 'english_CC.vtt' in n['name']:
                        vtt_url = n["name"]

                    if 'index.m3u8' in n['name'] and 'streaming_audio' not in n['name'] and 'streaming_video' not in n['name']:
                        m3u8_url = n["name"]



                if vtt_url != None and m3u8_url != None:

                    #ファイルをセーブするときエラーを避けるため
                    anime_episode_name = re.sub(r'[\\/:*?"<>|]', '', anime_episode['name'])
                    
                    vtt_name = idx + '_' + anime_episode_name + '.vtt'
                    srt_name = idx + '_' + anime_episode_name + '.srt'
                    m3u8_name = idx + '_' + anime_episode_name + '.m3u8'
                    video_name = idx + '_' + anime_episode_name + '.mp4'
                    
                    save_path2 = save_path + anime_name + '/'

                    createFolder(save_path2)

                    download(vtt_url, save_path2 + vtt_name)
                    download(m3u8_url, save_path2 + m3u8_name)
                    vtt_to_srt(save_path2 + vtt_name)
                    modify_srt_for_videostation(save_path2 + srt_name)
                    modify_m3u8(save_path2 + m3u8_name)

                    cmd = 'ffmpeg -y -protocol_whitelist file,http,https,tcp,tls,crypto' + ' -i \"' + save_path2 + m3u8_name + '\" -bsf:a aac_adtstoasc -c copy "' + save_path2 + video_name + '"'

                    print(idx, anime_episode['name'])
                    print(vtt_url)
                    print(m3u8_url)
                    print(cmd)
                    print()
                    
                    #幾つかのアニメを同時にダウンロードするため
                    t = threading.Thread(target=download_funimation_anime2, args=(cmd,save_path2 + m3u8_name))
                    t.daemon = True 
                    t.start()
                    thread_list.append(t)     


                    is_break = True
                    break

                time.sleep(1)

    driver.get(anime_url)
    
    driver.quit()
    
    #ダウンロードが終わるまで待機
    for t in thread_list:
        t.join()

    print(anime_name + " all ani download complete")

def download_funimation_anime2(cmd, file_name):
    os.system(cmd)
    os.remove(file_name)

def modify_m3u8(file_name):

    m3u8_list = []
    is_variants  = False
    is_end_variants = False
    is_keyframes = False

    with open(file_name, encoding='utf_8') as f:

        f = list(f)

        for idx, line in enumerate(f):

            if is_variants == False:
                m3u8_list.append(line)
            elif is_variants == True and is_end_variants == False:
                if '\n' == line:
                    m3u8_list.append(f[idx-2])
                    m3u8_list.append(f[idx-1])
                    m3u8_list.append(f[idx])
                    is_end_variants = True
            elif is_end_variants == True:

                if is_keyframes == False:
                    m3u8_list.append(line)

                elif is_keyframes == True:

                    if len(f)-1 == idx:
                        m3u8_list.append(f[idx-1])


            if '# variants' in line:
                is_variants = True
            elif '# keyframes' in line:
                is_keyframes = True

    os.remove(file_name)
    
    time.sleep(1)
        
    with open(file_name, 'a', encoding='utf_8') as f:
        for line in m3u8_list:
            f.write(line)
            
def modify_srt_for_videostation(file_name):
    srt_list = []
    with open(file_name, 'r', encoding='utf_8') as f:
        f = list(f)
        idx2 = 1
        for idx, line in enumerate(f):
            if idx > 0:
                if line == '\n' and idx != len(f)-1:
                    line = str(idx2) + '\n'
                    idx2 = idx2+1
                    
                    if idx != 1:
                        srt_list.append('\n')
                    
                srt_list.append(line)
                
    os.remove(file_name)
    
    with open(file_name, 'a', encoding='utf_8') as f:
        for line in srt_list:
            f.write(line)


user_id = input('Input Funimation id: ')
user_passwd = input('Input Funimation passwd: ')

anime_url = None

save_path = 'Downloaded/'



driver = driver_set()

driver.get("https://www.funimation.com/log-in/") #funimationからログインしてから次に進む

driver.find_element(By.XPATH, '//*[@id="email2"]').send_keys(user_id)
driver.find_element(By.XPATH, '//*[@id="password2"]').send_keys(user_passwd)
driver.find_element(By.XPATH, '//*[@id="login-form"]/div[2]/section[1]/div/div/div[2]/div/div/form').submit()
driver.implicitly_wait(5)
time.sleep(5)


driver.get("https://www.funimation.com/")


while(True):
    result = input("Press any key to download the anime.")
    
    anime_url = driver.current_url
    
    if 'https://www.funimation.com/shows/' in anime_url and anime_url != 'https://www.funimation.com/shows/':
        break
    else:
        print('Current Page Error, Example "https://www.funimation.com/shows/18if/"')
    



download_funimation_anime(driver, anime_url, save_path)