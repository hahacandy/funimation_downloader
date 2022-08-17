from webdriver_manager.chrome import ChromeDriverManager
from selenium import webdriver
from selenium.webdriver.common.by import By
import time
import os
import requests
import threading



def driver_set():
    option = webdriver.ChromeOptions()

    # Chrome v75 and lower:
    # option.add_argument("--headless") 
    # Chrome v 76 and above (v76 released July 30th 2019):

    # option.add_argument('--headless')
    option.add_argument('--start-maximized')
    option.add_argument("disable-gpu")
    option.add_argument("user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_12_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/61.0.3163.100 Safari/537.36")
    option.add_argument("lang=ko_KR") # 한국어!

    #option.add_argument('--no-sandbox')

    #option.add_argument('--disable-dev-shm-usage')

    #chrome_prefs = {}
    #option.experimental_options["prefs"] = chrome_prefs
    #chrome_prefs["profile.default_content_settings"] = {"images": 2}
    #chrome_prefs["profile.managed_default_content_settings"] = {"images": 2}
    #option.add_argument('--user-data-dir=' + os.getcwd() + '/files/dataDir')

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
    
    driver.get(anime_url)

    driver.implicitly_wait(5)

    anime_name = driver.find_element(By.XPATH, '//*[@id="main-content"]/div/div/div/div/section/div/div[3]/article/div/div/div[2]/div/div[1]/h1').text

    thumbnail_url = driver.find_element(By.XPATH, '//*[@id="main-content"]/div/div/div/div/section/div/div[3]/article/div/div/div[1]/div[1]/div[2]')
    thumbnail_url = thumbnail_url.get_attribute('style')[thumbnail_url.get_attribute('style').find('url("') + 5:thumbnail_url.get_attribute('style').find('jpg")') + 3]
    thumbnail_url

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

                    if 'm3u8' in n['name']:
                        m3u8_url = n["name"]



                if vtt_url != None and m3u8_url != None:

                    save_path2 = save_path + anime_name + '/'
                    vtt_name = str(idx) + '_' + anime_episode['name'] + '.vtt'
                    video_name = str(idx) + '_' + anime_episode['name'] + '.mp4'

                    createFolder(save_path2)

                    download(vtt_url, save_path2 + vtt_name)

                    cmd = 'ffmpeg -y -referer \"' + referer + '\" -i \"' + m3u8_url + '\" -bsf:a aac_adtstoasc -c copy "' + save_path2 + video_name + '"'

                    print(idx, anime_episode['name'])
                    print(vtt_url)
                    print(m3u8_url)
                    print(cmd)
                    print()
                    
                    #幾つかのアニメを同時にダウンロードするため
                    t = threading.Thread(target=download_funimation_anime2, args=(cmd,))
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

def download_funimation_anime2(cmd):
    os.system(cmd)



user_id = input('Input Funimation id: ')
user_passwd = input('Input Funimation passwd: ')

anime_url = input('Input Funimation Anime URL: ')

save_path = 'Y:/Eng_Animes/'



driver = driver_set()

driver.get("https://www.funimation.com/log-in/") #funimationからログインしてから次に進む

driver.find_element(By.XPATH, '//*[@id="email2"]').send_keys(user_id)
driver.find_element(By.XPATH, '//*[@id="password2"]').send_keys(user_passwd)
driver.find_element(By.XPATH, '//*[@id="login-form"]/div[2]/section[1]/div/div/div[2]/div/div/form').submit()
driver.implicitly_wait(5)
time.sleep(5)



download_funimation_anime(driver, anime_url, save_path)