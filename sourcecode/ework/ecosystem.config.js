module.exports = {
  apps : [{
    name: 'bt_gateway',
    script: 'bleak_v2.py',
    cwd: '/home/pi/ework/Bluetooth/',
    interpreter:'python3',
    watch:true,
    ignore_watch:'.',
   

    
  }, {
    name: 'backend',
    script: 'bt_webapi_v3.py',
    cwd: '/home/pi/ework/Bluetooth/',
    interpreter:'python3',
    watch:true,
    ignore_watch:'.'
    


  }, {
    name: 'frontend',
    script: 'index.js',
    cwd: '/home/pi/ework/Bluetooth/bt_frontend/',
    interpreter:'nodejs',
    watch: true,
    time: true
  }],

};

