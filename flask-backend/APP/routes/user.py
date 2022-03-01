from flask import Blueprint, make_response, request, jsonify
from APP.utils import query_db, query_commit_db


user_bp = Blueprint('user', __name__)

@user_bp.route("/get")
def get_users():
    query_res = query_db('select * from user')
    response = make_response(
                jsonify(
                    {"message": query_res}
                ),
                200,
            )
    # return query_db('select * from user')
    return response

@user_bp.route("/get_info")
def get_all_info():
    data = request.json
    if(data.get('Email_Id') is None):
        return make_response(jsonify({"message": "Not a Valid Email Id"}), 200)
    
    userData = {"Email_Id": data.get("Email_Id")}
    
    # Fetch mobile Numbers
    query_res = query_db('select DISTINCT Mobile_Number from User_Mobile_Number WHERE Email_Id = ?', (data.get('Email_Id'), ))
    userData["Mobile_Number"] = query_res

    # Fetch Addresses
    query_res = query_db('select DISTINCT * from Address WHERE Email_Id = ?', (data.get('Email_Id'), ))
    userData["Address"] = query_res

    # Fetch Name
    query_res = query_db('select Name from User WHERE Email_Id = ?', (data.get('Email_Id'), ), one=True)
    userData["Name"] = query_res["Name"]

    response = make_response(
                jsonify(
                    {"message": userData}
                ),
                200,
            )
    # return query_db('select * from user')
    return response

@user_bp.route("/add/", methods = ["POST"])
def add_users():
    data = request.json
    print(data)
    # return data
    query_res = True
    if(data.get('Email_Id') is None):
        return make_response(jsonify({"message": False}), 200)
    if(data.get('Name') is not None):
        query_res = query_commit_db(
            """
            INSERT INTO User (Email_ID, Name) values
            (?, ?)
            """,
            (data['Email_Id'], data['Name']),
            one=True
        )

    if(data.get('Mobile_Number') is not None):
        query_res = query_commit_db(
            """
            INSERT INTO User_Mobile_Number (Mobile_Number, Email_id) values (?, ?);
            """,
            [(number, data['Email_Id'],) for number in data['Mobile_Number']]
        )

    if(data.get('Address') is not None):
        query_res = query_commit_db(
            """
            INSERT INTO Address (House_No, Street, City, Country, PinCode, Email_Id) values (?, ?, ?, ?, ?, ?);
            """,
            [(House_No, Street, City, Country, PinCode, data['Email_Id'],) for House_No, Street, City, Country, PinCode in data['Address']]
        )
    
    if(data.get('Password') is not None):
        query_res = query_commit_db(
            """
            INSERT INTO LoginDetails (Email_ID, Password) values
            (?, ?)
            """,
            [(data['Email_Id'], data['Password'],)]
        )
    

    return make_response(jsonify({"message": query_res}), 200)