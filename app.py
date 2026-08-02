from flask import Flask, request, jsonify

app = Flask(__name__)

@app.route('/', methods=['GET'])
def home():
    return jsonify({"message": "COMPATH Backend API is running!"}), 200

@app.route('/api/signup', methods=['POST'])
def signup():
    return jsonify({"status": "success", "message": "Sign Up API is working!"}), 200

@app.route('/api/login', methods=['POST'])
def login():
    return jsonify({"status": "success", "message": "Login API is working!"}), 200

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)