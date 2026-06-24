function iotaShow(value) {
  document.getElementById('jsonView').textContent = JSON.stringify(value, null, 2);
}
function iotaMessage(text) {
  var log = document.getElementById('chatLog');
  var p = document.createElement('p');
  p.className = 'msg';
  p.textContent = text;
  log.appendChild(p);
}
console.log('IOTA workbench loaded');
