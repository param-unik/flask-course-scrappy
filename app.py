import os
import time
from flask import Flask, render_template, request,jsonify
from flask_cors import CORS,cross_origin
from bs4 import BeautifulSoup as bs
from urllib.request import urlopen as uReq
import urllib.request as urlRequest
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
import logging
import pymongo
from dotenv import load_dotenv

app = Flask(__name__)
logging.basicConfig(level=logging.DEBUG)

@app.route('/', methods=['GET'])  # route to display the home page
@cross_origin()
def homePage():
    app.logger.info('App is rendering index.html')
    return render_template("index.html")

def loadDB(courselist):
    try:
        # connecting to MOngoClient 
        client= pymongo.MongoClient(os.environ.get('DB_URL'))
        
        # connecting to iNeuron database 
        iNeuron = client['iNeuron']
        
        # connecting to courses collection inside iNeuron database 
        courses = iNeuron['courses']
        
        try:
            # inserting all extracted records to MongoDB using insert_many
            courses.insert_many(courselist)
        except: 
            app.logger.info("Error inserting data to mongodb")
    except:
        app.logger.info('error connecting to mongo db client')    

@app.route('/courses', methods=['POST', 'GET'])  # route to show the review comments in a web UI
@cross_origin()
def index():
    if request.method == 'POST':
        try:
            # below are chrome options for selenium
            load_dotenv()
            app.logger.info(os.environ.get('ENV')) 
            chrome_options = webdriver.ChromeOptions()
            chrome_options.add_argument('--headless')

            # below code will check whether we are in local or on server             
            if os.environ.get('ENV') != 'Prod':
                app.logger.info('Non prod environment is activated which is local env')
                driver = webdriver.Chrome(executable_path=r'C:\Users\Param\Downloads\ImageScrapper\ImageScrapper\chromedriver.exe', chrome_options=chrome_options)
            else:
                app.logger.info('Prod environment is activated')
                chrome_options.binary_location = os.environ.get("GOOGLE_CHROME_BIN")
                chrome_options.add_argument("--disable-dev-shm-usage")
                chrome_options.add_argument("--no-sandbox")
                driver = webdriver.Chrome(executable_path=os.environ.get("CHROMEDRIVER_PATH"), chrome_options=chrome_options)
                
            # base URL on which web scrape needs to be performed..
            iNeuron_url = "https://ineuron.ai/"

            # pretend to be a chrome 47 browser on a windows 10 machine
            headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/100.0.4896.88 Safari/537.36"}
            
            try:
                req = urlRequest.Request(iNeuron_url, headers = headers)
                # calling HTTP request 
                uClient = uReq(req)
                # try to read everything from webPage 
                iNeuronHomePage = uClient.read()
                uClient.close()
            except:
                app.logger.error("Error in establishing request with iNeuron")

            try:
                # it will help us to parse HTML related stuff 
                iNeuron_html = bs(iNeuronHomePage, "html.parser")
            except:
                app.logger.error("Not able to parse web page.") 

            try:  
                courseExplorer = iNeuron_html.findAll("div", {"class": "left-area"})
                coursesURL = courseExplorer[0].a['href']
                app.logger.info(coursesURL)
            except:
                app.loger.error("Error finding class or href of course URL")   

            app.logger.info("Dynamic scraping starts here")
            try:
                # since iNeuron has dynamic course website built in react so we need selenium driver to
                # scrape data
                driver.get(coursesURL)
                soup = bs(driver.page_source, 'html.parser')
                app.logger.info('soup')
                app.logger.info(soup)
            except:
                app.logger.error('Not able to parse dynamic page')

            try:    
                allCourses = soup.find_all('div', {'class': "TopCategoryList_categories__1oxks"})
                app.logger.info('All Courses')
                app.logger.info(allCourses)
            except:
                app.logger.error('Not able to locate div for course categories List')
            
            try:
                courseName = allCourses[0].find_all('p', {'class' : 'TopCategory_listname__BgEnP'})[0].text
            except:
                app.logger.info(allCourses)
                app.logger.error('Error getting course Name from paragraph')

            try:
                allcoursesURL = allCourses[0].div
                app.logger.info(allcoursesURL)
                href = allcoursesURL.find_all('a')
                app.logger.info(href)
            except:
                # app.logger.info(allcoursesURL)
                # app.logger.info(href)
                app.logger.error('Error getting courses from ancher tag')

            # defining empty list    
            courselist =[]

            # looping through each of sectionsg e.g -> Data Science, programming, cloud, Marketing , 
            for i in range(0, len(href)):
                courseName = allCourses[0].find_all('p', {'class' : 'TopCategory_listname__BgEnP'})[i].text
                app.logger.info(courseName)
                app.logger.info('**************************************')  
                new_cat_url = coursesURL + href[i]['href']
                app.logger.info(new_cat_url)

                try:
                    driver.get(new_cat_url)
                except:
                    app.logger.error('error getting URL extracted from anchor tag')

                # to scroll from 0 to end of page
                driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                
                # process will go for sleep for 15 minutes
                time.sleep(15)

                try:
                    course_page = bs(driver.page_source, 'html.parser')
                    all_course_list = course_page.find_all('div', {'class': 'AllCourses_course-list__36-kz'})
                except:
                    app.logger.error('Error getting courses from individual section')

                try:    
                    course_list  = all_course_list[0].div.div.find_all('div', {'class': 'Course_course-card__1_V8S Course_card__2uWBu card'})
                except:
                    app.logger.error('Error extracting div which has details of each of the courses section wise')

                app.logger.info(len(course_list))

                # running loop to get course title
                # course description, course fee and course instructors for each of the course
                for i in range(0, len(course_list)):
                    course_title = course_list[i].find_all('h5',  {'class': 'Course_course-title__2rA2S'})[0].text
                    course_desc  = course_list[i].find_all('div', {'class': 'Course_course-desc__2G4h9'})[0].text  
                    course_instr = course_list[i].find_all('div', {'class': 'Course_course-instructor__1bsVq'})
                    course_price = course_list[i].find_all('div', {'class': 'Course_price-div__3KBBq'})[0].div.h6.span.text 

                    try:
                        course_instr = course_instr[0].text 
                    except:
                        course_instr = 'No Instructor'

                    # Need to add the extracted details to python list
                    courselist.append({'Category': courseName, 'Sub Category' : course_title , 'Course Fee' : course_price,
                                    'Course Instructors' : course_instr, 'Course Desc': course_desc} )

                app.logger.info('**************************************') 
            app.logger.info('loading data to mongo db.')
            loadDB(courselist)
            # if all good then results.html will get render and show to the users.    
            return render_template('results.html', courselist=courselist[0:(len(courselist) - 1)])
        except Exception as e:
            app.logger.error(e)
            app.logger.error('Exception happened here..')
            return 'something is wrong'
    else:
        return render_template('index.html')


if __name__ == "__main__":
    app.run(host='127.0.0.1', port=8001, debug=True)

