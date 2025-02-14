from flask import Flask, redirect, url_for, g, render_template, session, request
from .routes import base_bp
from APP.utils import query_db, get_db, SCHEMA, login_required
from APP.routes.item import search_item_query
import os
import datetime
from decouple import config

# from flask_cors import CORS

# Main application and configuration
app = Flask(__name__)

# For Session
app.config['SECRET_KEY'] = config('SECRET_KEY')
app.config['SESSION_TYPE'] = 'memcached'
# app.config['SECRET_KEY'] = 'super secret key'
# Maybe required in future
# cors = CORS(app)

@app.template_filter('formatdatetime')
def format_datetime(value, format="%d %b %Y %I:%M %p"):
    """Format a date time to (Default): d Mon YYYY HH:MM P"""
    if value is None:
        return ""
    value = datetime.datetime.fromisoformat(value)
    return value.strftime(format)

app.register_blueprint(base_bp, url_prefix="/api")

def init_db():
    with app.app_context():
        db = get_db()
        with app.open_resource(SCHEMA, mode='r') as f:
            db.cursor().executescript(f.read())
        db.commit()


@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

@app.route('/favicon.ico')
def favicon():
    return app.send_static_file('favicon.ico')

@app.route('/')
def index(queryInfo = None):
    # cur = get_db().cursor()
    # for user in query_db('select * from user'):
    #     print(user)
    # return query_db('select * from user')
    # return "Hi"
    print(queryInfo)
    search_query = request.args.get('searchinput') if request.args.get('searchinput') is not None else ""
    response = search_item_query(search_query, queryInfo)
    print(response)
    g.items = response
    items = []
    for item in g.items:
        image_res = query_db(
            'SELECT ImageId from Item_Image where Item_Id = ?;',
            (item.get("Item_Id"),),False
        )
        if len(image_res) > 0:
            items.append(item)
            items[-1]['ImageId'] = image_res[0]['ImageId']
            if('user' in session):
                iswishlist = query_db('SELECT Count(*) AS cnt FROM Wishlist WHERE Item_Id = ? AND Email_Id = ?;', (item.get('Item_Id'), session.get('user').get('email')), True)
                if(iswishlist.get('cnt') > 0):
                    items[-1]['IsWishlisted'] = True
                else:
                    items[-1]['IsWishlisted'] = False
            else:
                items[-1]['IsWishlisted'] = False
        else:
            items.append(item)
            items[-1]['ImageId'] = -1
            if('user' in session):
                iswishlist = query_db('SELECT Count(*) AS cnt FROM Wishlist WHERE Item_Id = ? AND Email_Id = ?;', (item.get('Item_Id'), session.get('user').get('email')), True)
                if(iswishlist.get('cnt') > 0):
                    items[-1]['IsWishlisted'] = True
                else:
                    items[-1]['IsWishlisted'] = False
            else:
                items[-1]['IsWishlisted'] = False
    g.items = items
        # g.images.append(image_res['ImageId'])
    return render_template("index.html",cssfile="css/index.css")

@app.route('/myitems')
@login_required
def myitems():
    queryInfo = request.url.split('/')[-1]
    return index(queryInfo)

@app.route('/wishlist')
@login_required
def wishlist():
    queryInfo = request.url.split('/')[-1]
    return index(queryInfo)

@app.route('/login')
def login():
    # Logout if already logged in
    logout()
    return render_template("login.html",cssfile="css/login.css")

@app.route('/register')
def register():
    # Logout if already logged in
    logout()
    return render_template("register.html")

@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect(url_for('login'))


@app.route('/account')
@login_required
def account():
    # g is lika a global data that exist for a single request
    g.user = session.get('user')
    # print(g.user)
    # we can access g in templates (check email field)
    return render_template("account.html")

@app.route('/updateprofile')
@login_required
def updateprofile():
    # g is lika a global data that exist for a single request
    g.user = session.get('user')
    return render_template("updateprofile.html", cssfile="css/updateprofile.css")

@app.route("/additem")
@login_required
def additem():
    return render_template("additem.html")

@app.route("/addadvert")
@login_required
def addadvert():
    return render_template("addadvert.html")

@app.route("/item/<itemid>")
def viewitem(itemid):
    query_res = query_db(
        '''
        SELECT 
        I.Name as ItemName, Description, I.Item_Id, U.Email_Id, U.Name as UserName, avg(Rating) as Average_Rating 
        FROM 
        Item as I 
        Join User as U 
        on I.Email_Id = U.Email_Id 
        LEFT Join Reviews 
        on I.Item_Id = Reviews.Item_Id
        where I.Item_Id =?
        GROUP BY I.Name , Description, I.Item_Id, U.Email_Id, U.Name''',
        (itemid,),
        True
    )
    if (query_res is None):
        return "Item not found", 404
    image_res = query_db(
        'SELECT ImageId from Item_Image where Item_Id = ?;',
        (itemid,),
    )
    bid_res = query_db(
        '''
        SELECT Bid.*, User.Name as BidderName
        FROM 
        Item 
        JOIN SaleAdvertisement ON Item.Item_Id = SaleAdvertisement.Item_Id
        JOIN Bid ON Bid.AdvertisementId = SaleAdvertisement.AdvertisementId 
        JOIN USER ON User.Email_Id = Bid.Bidder_Id 
        WHERE SaleAdvertisement.End_Date is NULL 
        AND Item.Item_Id = ?
        ORDER BY Bid.Cost DESC;
        ''',
        (itemid,)
    )
    transactons_res = query_db('''
    SELECT Transactions.*, Buyer.Name as BuyerName, Seller.Name as SellerName 
    FROM Transactions 
    JOIN User As Buyer 
    ON Transactions.BuyerEmail_Id = Buyer.Email_Id 
    JOIN User As Seller 
    ON Transactions.SellerEmail_Id = Seller.Email_ID
    WHERE Item_Id = ?
    ORDER BY Transactions.Date DESC;
    ''',(itemid,))
    wishlistRes = query_db('SELECT COUNT(*) AS wishlistcnt FROM WISHLIST WHERE ITEM_Id = ?', (itemid,), True)
    g.isWishlist = False
    g.canSell = False
    g.canAddAdvert = False
    g.isOwner = False
    if(session.get('user') is not None):
        isWishListRes = query_db('SELECT COUNT(*) AS wishlistcnt FROM WISHLIST WHERE ITEM_Id = ? AND Email_Id = ? ', (itemid,session.get('user').get('email'),), True)
        g.isWishlist = (isWishListRes.get('wishlistcnt') > 0)
        g.canSell = (query_res.get('Email_Id') == session.get('user').get('email') and len(bid_res)>0)
        g.canAddAdvert = (query_res.get('Email_Id') == session.get('user').get('email') and (len(bid_res) == 0))
        g.isOwner = (query_res.get('Email_Id') == session.get('user').get('email'))
    print(g.canSell)
    g.wishlistCnt = wishlistRes.get('wishlistcnt')
    g.item = query_res
    g.images = [img['ImageId'] for img in image_res]
    g.bids = bid_res
    g.transactions = transactons_res
    
    if(g.item is None):
        return redirect(url_for('account'))

    return render_template("itempage.html", cssfile="css/itempage.css")


@app.route("/map")
def get_map():
    data={}
    for rule in app.url_map.iter_rules():
        try:
            data[str(rule.endpoint)]=str(url_for(rule.endpoint))
        except:
            pass
    return data
