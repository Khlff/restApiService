import pip
pip.main(['install', 'mysql-connector-python'])
import mysql.connector

from flask import Flask, jsonify, request
from flask_restful import Api, Resource
from config import host, port, user, password, database
import traceback

app = Flask(__name__)
app.config['JSON_SORT_KEYS'] = False
api = Api()


class Imports(Resource):
    def post(self):
        content = request.json
        if len(content) < 2:
            return {"code": 400, "message": "Validation Failed"}, 400

        receivedItems = content['items']
        updateDate = content['updateDate']

        id_list = []

        # Try to connect to db
        try:
            connection = mysql.connector.connect(host=host, port=port, user=user, password=password, database=database)
            with connection.cursor() as cur:

                sql = "INSERT INTO item (`id`, `name`, `parentId`, `price`, `type`,`date`) VALUES (%s,%s,%s,%s,%s,%s) " \
                      "ON DUPLICATE KEY UPDATE name = %s, parentId = %s, price = %s, type = %s, date = %s"

                for item in receivedItems:

                    if item['name'] is None or item['id'] in id_list:
                        return {"code": 400, "message": "Validation Failed"}, 400

                    if item['type'] == 'CATEGORY':

                        cur.execute(sql, (item['id'], item['name'], item['parentId'], None, item['type'], updateDate,
                                          item['name'], item['parentId'], None, item['type'], updateDate))

                    else:
                        cur.execute(sql, (
                            item['id'], item['name'], item['parentId'], item['price'], item['type'], updateDate,
                            item['name'], item['parentId'], item['price'], item['type'], updateDate))
                    id_list.append(item['id'])

                parList = []
                for item in id_list:
                    bFlag = True
                    searchId = item
                    while bFlag:
                        cur.execute(f"SELECT `parentId` FROM item WHERE id = '{searchId}'")
                        parent = cur.fetchone()
                        if parent is not None:
                            if parent[0] is not None:
                                parList.append(parent[0])
                                searchId = parent[0]
                            else:
                                bFlag = False
                        else:
                            bFlag = False
                for idOfItem in set(parList):
                    sql = f"UPDATE item set date = '{updateDate}' where id = '{idOfItem}'"
                    cur.execute(sql)

            connection.commit()
            return jsonify({"code": 200})
        except Exception as ex:
            print(traceback.format_exc())
            return {"code": 400, "message": "Validation Failed"}, 400


class Nodes(Resource):
    def get(self, uuid):
        # Try to connect to db
        try:
            connection = mysql.connector.connect(host=host, port=port, user=user, password=password, database=database)
            with connection:
                with connection.cursor() as cur:
                    cur.execute(f"SELECT * FROM item WHERE id = '{uuid}'")
                    takenFirst = cur.fetchone()

                    if takenFirst is None:
                        return {"code": 404, "message": "Item not found"}, 404
                    keys = ["id", "name", "parentId", "price", "type", "date"]
                    mainResponse = {}

                    # Take first item from answer response
                    for i in range(len(takenFirst)):
                        if keys[i] == "date":
                            mainResponse[keys[i]] = str(takenFirst[i])
                        else:
                            mainResponse[keys[i]] = takenFirst[i]

                    # If the first element is a category - we get all the branches
                    if mainResponse['type'] == 'CATEGORY':

                        cur.execute(
                            f"with recursive cte (id, name, parentId,price,type,date) as ( select id, name, parentId, price, type, date from item where parentId = '{uuid}' "
                            f"union all select i.id, i.name, i.parentId, i.price,i.type,i.date from item i inner join cte on i.parentId = cte.id ) "
                            f"select * from cte"
                        )

                        keys = ["id", "name", "parentId", "price", "type", "date"]
                        answerFromDb = cur.fetchall()
                        listWithAllItems = []

                        # Build list with all items
                        for sp in answerFromDb:
                            dict = {}
                            for i in range(len(sp)):
                                if keys[i] == "date":
                                    dict[keys[i]] = str(sp[i])
                                else:
                                    dict[keys[i]] = sp[i]
                            if dict['type'] == 'OFFER':
                                dict['children'] = None
                            listWithAllItems.append(dict)

                        # Calculation of the cost of goods and their quantity in each category
                        categoryPrices = {}
                        categoryNumberOfItems = {}
                        categoryList = {}
                        categorySubList = {}
                        for elem in listWithAllItems:
                            if elem['parentId'] is not None:
                                if elem['type'] != 'CATEGORY':
                                    if elem['parentId'] not in categoryPrices.keys():
                                        categoryPrices[elem['parentId']] = elem['price']
                                        categoryNumberOfItems[elem['parentId']] = 1
                                    else:
                                        categoryPrices[elem['parentId']] += elem['price']
                                        categoryNumberOfItems[elem['parentId']] += 1
                                else:
                                    categoryList[elem['id']] = elem
                                    if elem['parentId'] not in categorySubList.keys():
                                        categorySubList[elem['parentId']] = [elem['id']]

                                    else:
                                        categorySubList[elem['parentId']].append(elem['id'])

                        while len(categorySubList) != 0:
                            for item in categoryList:
                                if categoryList[item] is not None:
                                    if categoryList[item]['parentId'] is not None:
                                        if item not in categorySubList.keys():
                                            if categoryList[item]['parentId'] in categoryPrices.keys():
                                                categoryPrices[categoryList[item]['parentId']] += categoryPrices[item]
                                                categoryNumberOfItems[categoryList[item]['parentId']] += \
                                                    categoryNumberOfItems[item]
                                            categorySubList[categoryList[item]['parentId']].remove(item)
                                            if len(categorySubList[categoryList[item]['parentId']]) == 0:
                                                del categorySubList[categoryList[item]['parentId']]
                                            categoryList[item] = None

                        # Distribution of children in each category
                        for child in listWithAllItems:
                            if child['id'] in categoryPrices:
                                child['price'] = int(categoryPrices[child['id']] / categoryNumberOfItems[child['id']])
                            if child['parentId'] is not None:
                                for parent in listWithAllItems:
                                    if parent['id'] == child['parentId']:
                                        if 'children' in parent.keys():
                                            parent['children'].append(child)
                                        else:
                                            parent['children'] = [child]

                        res = []
                        for i in listWithAllItems:
                            if i['parentId'] == mainResponse['id']:
                                res.append(i)

                        if len(res) != 0:
                            mainResponse['children'] = res

                        mainResponseSum = 0
                        mainResponseCount = 0
                        for i in categoryPrices:
                            mainResponseSum += categoryPrices[i]
                        for i in categoryNumberOfItems:
                            mainResponseCount += categoryNumberOfItems[i]

                        mainResponse['price'] = int(mainResponseSum / mainResponseCount)

                        return jsonify(mainResponse)

                    # If the requested item is a product
                    else:
                        return jsonify(mainResponse)

        except Exception as ex:
            print(traceback.format_exc())
            return {"code": 400, "message": "Validation Failed"}, 400


class Delete(Resource):
    def delete(self, uuid):
        # Try to connect to db
        try:
            connection = mysql.connector.connect(host=host, port=port, user=user, password=password, database=database)
            with connection.cursor() as cur:
                sql = f"DELETE FROM item WHERE item.id = '{uuid}'"
                if cur.execute(sql) == 0:
                    return {"code": 404, "message": "Item not found"}, 404
                sql = f"with recursive cte (id, parentId) " \
                      f"as ( select id, parentId from item where parentId = '{uuid}' " \
                      f"union all " \
                      f"select i.id,  i.parentId from item i " \
                      f"inner join cte on i.parentId = cte.id ) " \
                      f"select * from cte"
                cur.execute(sql)
                idList = cur.fetchall()
                for id in idList:
                    sql = f"DELETE FROM item WHERE item.id = '{id[0]}'"
                    cur.execute(sql)
            connection.commit()
            return {"code": 200}, 200
        except Exception as ex:
            print('Connection refused')
            print(ex)
            return {"code": 400, "message": "Validation Failed"}, 400


api.add_resource(Imports, "/imports")
api.add_resource(Nodes, "/nodes/<string:uuid>")
api.add_resource(Delete, "/delete/<string:uuid>")
api.init_app(app)

if __name__ == "__main__":
    app.run(debug=False, port=80, host="0.0.0.0")
