# Importing necessary Libraries
from flask import Flask, render_template, request
import requests
from bs4 import BeautifulSoup as bs
from urllib.request import urlopen as ureq
from mysql import connector as con

app = Flask(__name__)  # initialising the flask app with the name 'app'

# This function will load home page to get user input
@app.route('/', methods=['GET'])
def homepage():
    return render_template('index.html')

# This function will scrap data from the website if reviews of product are not present in database and show in another html page
@app.route('/scrap',methods=['POST']) # route with allowed methods as POST and GET
def index():
    if request.method == 'POST':
        searchstring = request.form['content'].replace(" ","") # obtaining the search string entered in the form
        reviews = [] # To store the reviews in dictionary which will be passed to html page
        try:
            # Connecting to the MySQL server
            db_con = con.connect(host=host, user=user, password=password)
            print("Connected with MySQL Server : ", db_con.is_connected())

            db_con.autocommit = True  # To save the transactions in the database/table
            cur = db_con.cursor()  # Creating cursor which will be used to send commands to SQL server

            # Creating new database where reviews of various products will be stored in different tables
            cur.execute("""create database if not exists reviews;""")
            cur.execute("""use reviews;""")

            # Creating table (if not exists) which will store the information related to reviews of the product
            cur.execute(
                f"""create table if not exists {searchstring}(user varchar(99),rating varchar(5),CommentHeading varchar(50),Comment varchar(5000));""")

            # Checking if table(if table exists already) holds any reviews inside and getting number of records the table holds
            cur.execute(f"""select * from {searchstring}""")
            length = len(cur.fetchall())

            # If Number of reviews are more than 10 then print the reviews of the product from the table instead of scrapping data from the website
            if length > 10:
                cur.execute(f"""select user,rating,CommentHeading,Comment from {searchstring}""")
                db_reviews=cur.fetchall()
                for review in db_reviews:
                    name = review[0]
                    rating = review[1]
                    commentHead = review[2]
                    custComment = review[3]
                    mydict = {"Product": searchstring, "Name": name, "Rating": rating, "CommentHead": commentHead,
                                        "Comment": custComment} # saving that detail to a dictionary
                    reviews.append(mydict)

            else:
                # Code to scrape data
                flipkart_url = "https://www.flipkart.com/search?q=" + searchstring
                uclient = ureq(flipkart_url)
                flipkartpage = uclient.read()
                uclient.close()
                flipkart_html = bs(flipkartpage, "html.parser")
                bigboxes = flipkart_html.findAll("div", {"class": "_1AtVbE col-12-12"})
                del bigboxes[0:3]
                box = bigboxes[0]
                productlink = "https://www.flipkart.com" + box.div.div.div.a['href']
                
                prodres = requests.get(productlink)
                prod_html = bs(prodres.text, "html.parser")
                allreviews = prod_html.find("div", {"class": "col JOpGWq"})
                total_pages = int(int(allreviews.find("div", {"class": '_3UAT2v _16PBlm'}).text[4:-8]) / 10) + 2
                linker = "https://www.flipkart.com" + allreviews.findAll("a")[-1]['href']  # +"&page=3" # to get link of all reviews
                
                for i in range(1, total_pages):
                    fulllink = linker + f"&page={i}"
                    openlink = requests.get(fulllink)
                    openlinkhtml = bs(openlink.text, "html.parser")
                    commentboxes = openlinkhtml.find_all('div', {'class': "_27M-vq"})

                    #  iterating over the comment section to get the details of customer and their comments
                    for commentbox in commentboxes:
                        try:
                            name = commentbox.div.div.find_all('p', {'class': '_2sc7ZR _2V5EHH'})[0].text
                        except:
                            name = 'No Name'

                        try:
                            rating = commentbox.div.div.div.div.text
                        except:
                            rating = 'No Rating'

                        try:
                            commentHead = commentbox.div.div.div.p.text
                        except:
                            commentHead = 'No Comment Heading'

                        try:
                            comtag = commentbox.div.div.find_all('div', {'class': 't-ZTKy'})
                            custComment = comtag[0].find("div", {"class": ""}).text[:-9]
                        except:
                            custComment = 'No Customer Comment'

                        mydict = {"Product": searchstring, "Name": name, "Rating": rating, "CommentHead": commentHead,
                                  "Comment": custComment}  # saving that detail to a dictionary
                        reviews.append(mydict)
                print(reviews)
                for review in range(len(reviews)):
                    name = reviews[review]['Name'].replace("'", "\\'")
                    rating = reviews[review]['Rating'].replace("'", "\\'")
                    CommentHeading = reviews[review]['CommentHead'].replace("'", "\\'")
                    Comment = reviews[review]['Comment'].replace("'", "\\'")

                    try:
                        cur.execute(
                            f"""insert into {searchstring} values('{name}','{rating}','{CommentHeading}','{Comment}')""")
                    except:
                        continue
            cur.close()
            db_con.close()
            return render_template('results.html', reviews=reviews) # showing the review to the user
        except Exception as error :
            return f'something is wrong : {error}'


if __name__ == "__main__":
    host = "localhost"
    user = "root"
    password = "mysql"
    app.run(port=8000,debug=True) # running the app on the local machine on port 8000
