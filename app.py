from flask import Flask, make_response
from flask_restful import Resource, Api, reqparse
from flask_cors import CORS
from threading import Thread
from poe_api_wrapper import PoeApi
import time
import uuid
import json

app = Flask(__name__)
api = Api(app)
CORS(app, resources={r"/*": {"origins": "*"}})

# Global variable
chatbotName = 'open-bi-platform'

threads = {}

parser = reqparse.RequestParser()
parser.add_argument('key', type=str, required=True, help='Key cannot be blank.')
parser.add_argument('message', type=str, required=True, help='Message cannot be blank.')

@api.representation('application/json')
def output_json(data, code, headers=None):
    resp = make_response(json.dumps(data, ensure_ascii=False), code)
    resp.headers.extend(headers or {})
    return resp

class WorkerThread(Thread):
    
    def __init__(self, key, message, request_key):
        super().__init__()
        self.key = key
        self.message = message
        self.request_key = request_key
        
    def run(self):
        try:
            # Import poe key
            client = PoeApi(self.key, proxy=False)
            
            # execute message
            for chunk in client.send_message(chatbotName, self.message):
                pass
            result = chunk["text"]
            
            # Get chatCode from the last message
            chatCode = chunk["chatCode"]
            
            # Delete chat using chatCode
            client.delete_chat(chatbotName, chatCode=chatCode)
            
            time.sleep(5)
            
            print (result)
            
            threads[self.request_key]['result'] = result
            threads[self.request_key]['finished'] = True
        except Exception as e:
            return {
                'code': 400,
                'data': None,
                'message': 'Call AI service failed.'
            }, 400
            
class PoeChatAPI(Resource):

    def post(self):
        try:
            args = parser.parse_args()
        except Exception as e:
            return {
                'code': 400,
                'data': None,
                'message': 'Request body is not JSON format.'
            }, 400
            
        key = args['key']
        message = args['message']
        
        request_key = str(uuid.uuid4())
        thread = WorkerThread(key, message, request_key)
        threads[request_key] = {'thread': thread, 'finished': False, 'result': ''}
        
        thread.start()
        
        while True:
            if threads[request_key]['finished']:
                result = threads[request_key]['result']
                
                response = {
                    'code': 0,
                    'data': {
                        'content': result
                    },
                    message: 'ok.'
                }
                
                return response, 200
            
            time.sleep(0.2)

# Register API
api.add_resource(PoeChatAPI, '/api/exec')

if __name__ == '__main__':
    app.run()