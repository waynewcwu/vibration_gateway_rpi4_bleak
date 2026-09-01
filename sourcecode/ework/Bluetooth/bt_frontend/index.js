const fs = require('fs')
const express = require('express')
const path = require('path')
const bodyParser = require('body-parser')
const ping = require('ping')
const ip = require('ip')
const formidable = require('formidable')
const SocketServer = require('ws').Server

const MCU_FOLDER_PATH=process.env.BT_BIN_DIR || path.resolve(__dirname, '..', 'Bin')
const LOG_FOLDER_PATH=process.env.BT_LOG_DIR || path.resolve(__dirname, '..', 'log')
const FRONTEND_LOG_PATH=path.join(LOG_FOLDER_PATH, "frontend_logs.txt")
const ERROR_LOG_PATH=path.join(LOG_FOLDER_PATH, "error_log.txt")
const PING_RECORD_PATH=path.join(LOG_FOLDER_PATH, "ping_record.txt")
const PORT="8081"

fs.mkdirSync(LOG_FOLDER_PATH, {recursive:true})

var mWebSocket=[]
var mPingTimer
var IP=getLocalHostIP()
var jsonParser = bodyParser.json()

const app = express()
app.use('/libs', express.static('libs'))
app.use('/images', express.static('images'))
app.use(bodyParser.urlencoded({extended:false}))
app.use(bodyParser.json())
app.use(bodyParser.raw())
app.use(bodyParser.text())

process.on('uncaughtException', function(err) {
    console.log(err);
    try {
        fs.appendFileSync(ERROR_LOG_PATH, err);
    } catch(err) {
        console.log(err)
    }
})

const server = app.listen(PORT, () => {
	console.log("Listening on port:"+ PORT)
})

const wss = new SocketServer({server})
wss.on('connection', ws => {
    console.log('ws connection')
    mWebSocket.push(ws)

    ws.on('close', function incoming(message) {
        console.log('ws close')
        for(var i=0;i<mWebSocket.length;i++) {
            console.log("websocket on closed==>" + mWebSocket[i].readyState)
            if(mWebSocket[i].readyState==ws.CLOSED) {
                mWebSocket.splice(i,1)
            }
        }
    })
})

app.get('/', (req, res) => {
    fs.readFile('./html/ble.html', function(err, data) {
        res.write(data)
        return res.end()
    })
})

app.get('/ble', (req, res) => {
    fs.readFile('./html/ble.html', function(err, data) {
        res.write(data)
        return res.end()
    })
})

app.get('/mcu_setting', (req, res) => {
    fs.readFile('./html/mcu_setting.html', function(err, data) {
        res.write(data)
        return res.end()
    })
})

app.get('/network_setting', (req, res) => {
    fs.readFile('./html/network_setting.html', function(err, data) {
        res.write(data)
        return res.end()
    })
})

app.get('/connection_status', (req, res) => {
    fs.readFile('./html/connection_status.html', function(err, data) {
        res.write(data)
        return res.end()
    })
})

app.get('/log_checking', (req, res) => {
    fs.readFile('./html/log_checking.html', function(err, data) {
        res.write(data)
        return res.end()
    })
})

app.get('/notes', (req, res) => {
    fs.readFile('./html/notes.html', function(err, data) {
        res.write(data)
        return res.end()
    })
})

app.post('/get/ip', (req, res) => {
    IP=getLocalHostIP()
    console.log("get ip address:"+IP)
    res.end(IP)
})

app.post('/get/log', function(req, res) {
    var file_path=path.resolve(LOG_FOLDER_PATH, req.body.path)
    fs.readFile(file_path, function(err, data) {
        res.write(data)
        return res.end()
    })
})

app.post('/get/mcu_file_path',(req, res) => {
    var data={}
    var filenames=[]
    fs.readdirSync(MCU_FOLDER_PATH).forEach(file => {
        var file_path = path.resolve(MCU_FOLDER_PATH, file)
        if(fs.statSync(file_path).isFile()) {
            filenames.push(file)
        }
    })
    data["filenames"]=filenames
    data["path"]=MCU_FOLDER_PATH
    res.end(JSON.stringify(data))
})

app.post('/get/mcu_file_size',(req, res) => {
    var stat = fs.statSync(MCU_FOLDER_PATH + "/" + req.body.mcu_file_name)
    res.end(stat.size.toString())
})

app.post('/get/log_file_path',(req, res) => {
    var data={}
    var filenames=[]
    fs.readdirSync(LOG_FOLDER_PATH).forEach(file => {
        var file_path=path.resolve(LOG_FOLDER_PATH, file)
        if(fs.statSync(file_path).isFile()) {
            filenames.push(file)
        }
    })
    data["filenames"]=filenames
    data["path"]=LOG_FOLDER_PATH
    res.end(JSON.stringify(data))
})

app.post('/write/frontend_log',(req, res) => {
    try {
        fs.appendFileSync(FRONTEND_LOG_PATH, req.body.frontend_log);
    } catch(err) {
        console.log(err)
    }
    res.end()
})

app.post('/get/frontend_log',(req, res) => {
    fs.readFile(FRONTEND_LOG_PATH, function(err, data) {
        res.write(data);
        return res.end();
    })
})

app.post('/upload/file',(req, res) => {
    const form = new formidable.IncomingForm();
    form.parse(req, function(err, fields, files) {
        if(err) {
            console.log(err);
            res.end('File upload fail!');
        }
        
        console.log("files info: "+ JSON.stringify(files))

        var oldpath = files.mcu_bin.path;
        var newpath = path.join(MCU_FOLDER_PATH, files.mcu_bin.name)
        fs.rename(oldpath, newpath, function (err) {
            if(err) {
                console.log(err);
                res.end('File upload fail!');
            }

            res.end("File upload success!");
        });
    });
})

app.post('/start/ping',(req, res) => {
    var period=req.body.period*60*1000
    console.log("period:" + req.body.period + " minutes")
    let hosts=[req.body.server_ip]
    var response=getCurrentTime() + " Start ping " + "\n"
    mWebSocket.forEach(
        websocket => websocket.send(
            JSON.stringify({
                "command":"start",
                "message":response,
                "server_ip":req.body.server_ip,
                "mail_server_ip":req.body.mail_server_ip,
                "period":req.body.period
            })
        )
    )
    saveLog(response)

    mPingTimer=setInterval(function() {
        performPing(hosts)
    }, period)

    res.end(response)
})

app.post('/stop/ping',(req, res) => {
    var response=getCurrentTime() + " Stop ping " + "\n"
    mWebSocket.forEach(
        websocket => websocket.send(
            JSON.stringify({
                "command":"stop",
                "message":response
            })
        )
    )
    saveLog(response)

    mPingTimer=clearInterval(mPingTimer)
    console.log("mPingTimer==>"+mPingTimer)
    res.end(response)
})

app.post('/is/pinging',(req, res) => {
    if(typeof mPingTimer==='undefined') {
        res.end("false")
    } else {
        res.end("true")
    }
})

function getLocalHostIP() {
    return ip.address()
}

async function performPing(hosts) {
    for(let host of hosts){
        let res = await ping.promise.probe(host,{
            min_reply:4,
        })

        var response="";
        if(res.alive) {
            response="Host " + host + " is alive."
            response=getCurrentTime() + " " + response + "\n"
        } else {
            response="Host " + host + " not responses." + res.output
            response=getCurrentTime() + " " + response + "\n"
            saveLog(response)
        }
        
        mWebSocket.forEach(
            websocket => websocket.send(
                JSON.stringify({
                    "command":"info",
                    "message":response
                })
            )
        )
    }
}

function saveLog(logs) {
    var date = new Date();
    var today = date.getFullYear() + '-' + (date.getMonth()+1) + '-' + date.getDate();

    try {
        fs.appendFileSync(today + ".log", logs);
    } catch(err) {
        console.log(err)
    }
}

function getCurrentTime() {
    var today = new Date();
    var date = today.getFullYear()+'-'+(today.getMonth()+1)+'-'+today.getDate();
    var time = today.getHours() + ":" + today.getMinutes() + ":" + today.getSeconds();
    var dateTime = "[" + date + ' ' + time + "]";
    return dateTime
}
