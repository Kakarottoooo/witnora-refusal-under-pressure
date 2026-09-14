// TEST-ONLY forwarder so the WSL-isolated agent can reach the sanctioned host gateway channel.
// Binds 0.0.0.0:<LPORT> -> 127.0.0.1:8792. Token-gated by the gateway itself. Not part of the
// production deployment; it only relays the agent's normal Gateway submit channel across the WSL boundary.
import net from 'node:net';
const LPORT=Number(process.argv[2]||18792), THOST='127.0.0.1', TPORT=8792;
net.createServer(c=>{const u=net.connect(TPORT,THOST);c.pipe(u);u.pipe(c);c.on('error',()=>u.destroy());u.on('error',()=>c.destroy());})
  .listen(LPORT,'0.0.0.0',()=>console.log('forwarder listening 0.0.0.0:'+LPORT+' -> '+THOST+':'+TPORT));
