module.exports = async function handler(req, res) {
  console.log('[Test] Function called!');
  console.log('[Test] Method:', req.method);
  console.log('[Test] URL:', req.url);
  
  res.setHeader('Content-Type', 'application/json');
  res.status(200).json({ 
    message: 'API function is working!',
    method: req.method,
    url: req.url,
    query: req.query,
    timestamp: new Date().toISOString()
  });
}

