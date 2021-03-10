$(document).ready(function(){

var received = $('#received');


var socket = new WebSocket("ws://192.168.1.118:8080/ws");
 
socket.onopen = function(){  
  console.log("connected"); 
}; 

socket.onmessage = function (message) {
    weight = message.data;
    //weight = weight.replace(/(\r\n|\n|\r)/gm, "");
    //console.log("LW:", weight)
        document.getElementById('weight').innerHTML = weight;
//    document.getElementById('weight').innerHTML = $('#weight');
//    $('#weight').addClass('stable');
  console.log("receiving: " + message.data);
  //received.append(message.data);
  //received.append($('<br/>'));
};

socket.onclose = function(){
  console.log("disconnected"); 
};

var sendMessage = function(message) {
  console.log("sending:" + message.data);
  socket.send(message.data);
};


// GUI Stuff


// send a command to the serial port
$("#cmd_send").click(function(ev){
  ev.preventDefault();
  var cmd = $('#cmd_value').val();
  sendMessage({ 'data' : cmd});
  $('#cmd_value').val("");
});

$('#clear').click(function(){
  received.empty();
});


});
