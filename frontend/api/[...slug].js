/**
 * Vercel Serverless Function to proxy API requests to the backend
 * Uses catch-all route [...slug] to handle all /api/* requests
 */

const BACKEND_URL = process.env.BACKEND_URL || 'http://54.198.232.153:8000';

export default async function handler(req, res) {
  console.log(`[Proxy] ========== FUNCTION CALLED ==========`);
  console.log(`[Proxy] Method: ${req.method}`);
  console.log(`[Proxy] URL: ${req.url}`);
  console.log(`[Proxy] Query:`, JSON.stringify(req.query));
  console.log(`[Proxy] BACKEND_URL: ${process.env.BACKEND_URL || 'NOT SET - using default'}`);
  console.log(`[Proxy] Headers:`, JSON.stringify(req.headers));
  
  // Set CORS headers first
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS, PATCH');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type, Authorization');

  // Handle OPTIONS preflight
  if (req.method === 'OPTIONS') {
    console.log('[Proxy] Handling OPTIONS request');
    return res.status(200).end();
  }

  // Log all methods
  console.log(`[Proxy] Handling ${req.method} request`);

  try {
    // Get the path segments from the slug parameter
    const slug = req.query.slug || [];
    let apiPath = Array.isArray(slug) ? slug.join('/') : slug;
    
    console.log(`[Proxy] Slug:`, slug);
    console.log(`[Proxy] API Path (before clean):`, apiPath);
    
    // Remove leading 'api' if present (shouldn't happen, but just in case)
    if (apiPath.startsWith('api/')) {
      apiPath = apiPath.replace(/^api\//, '');
    }
    
    // Build backend URL
    // Most endpoints are under /api/, but /health is at root level
    // Root-level endpoints: '', 'health'
    const rootEndpoints = ['', 'health'];
    const isRootEndpoint = rootEndpoints.includes(apiPath);
    
    // Construct the backend URL
    let backendUrl;
    if (isRootEndpoint) {
      // Root-level endpoints: / or /health
      backendUrl = apiPath === '' ? `${BACKEND_URL}/` : `${BACKEND_URL}/${apiPath}`;
    } else {
      // All other endpoints are under /api/
      backendUrl = `${BACKEND_URL}/api/${apiPath}`;
    }
    
    // Add query parameters (excluding slug)
    const queryParams = new URLSearchParams();
    Object.keys(req.query).forEach(key => {
      if (key !== 'slug') {
        queryParams.append(key, req.query[key]);
      }
    });
    
    const queryString = queryParams.toString();
    const fullUrl = queryString ? `${backendUrl}?${queryString}` : backendUrl;
    
    console.log(`[Proxy] Backend URL: ${fullUrl}`);
    console.log(`[Proxy] Content-Type: ${req.headers['content-type'] || 'none'}`);
    
    // Prepare fetch options
    const fetchOptions = {
      method: req.method,
      headers: {},
    };
    
    // Copy all relevant headers
    Object.keys(req.headers).forEach(key => {
      const lowerKey = key.toLowerCase();
      if (!['host', 'connection', 'content-length', 'transfer-encoding'].includes(lowerKey)) {
        if (req.headers[key]) {
          fetchOptions.headers[key] = req.headers[key];
        }
      }
    });
    
    // Handle request body
    if (['POST', 'PUT', 'PATCH'].includes(req.method)) {
      const contentType = req.headers['content-type'] || '';
      console.log(`[Proxy] Has body: ${!!req.body}`);
      console.log(`[Proxy] Body type: ${typeof req.body}`);
      console.log(`[Proxy] Content-Type: ${contentType}`);
      
      if (contentType.includes('multipart/form-data')) {
        // For multipart/form-data, we need to preserve the raw body
        // Vercel serverless functions may parse it, but we need the raw stream
        // The body should be available as a buffer or stream
        console.log('[Proxy] Handling multipart/form-data');
        console.log('[Proxy] Body is buffer:', Buffer.isBuffer(req.body));
        console.log('[Proxy] Body type:', typeof req.body);
        console.log('[Proxy] Body constructor:', req.body?.constructor?.name);
        
        // Try to get raw body - Vercel might provide it as a buffer
        if (Buffer.isBuffer(req.body)) {
          // Perfect - we have a raw buffer, pass it through
          fetchOptions.body = req.body;
          fetchOptions.headers['Content-Type'] = contentType; // Preserve boundary
        } else if (req.body && typeof req.body === 'object' && req.body.pipe) {
          // It's a stream - we'd need to buffer it, but for now try to pass
          fetchOptions.body = req.body;
          fetchOptions.headers['Content-Type'] = contentType;
        } else {
          // Body was parsed - this is problematic for multipart
          // We need to reconstruct it using form-data
          console.log('[Proxy] WARNING: Multipart body was parsed, attempting reconstruction');
          console.log('[Proxy] Body keys:', req.body ? Object.keys(req.body) : 'null');
          
          // Try to reconstruct using form-data library
          try {
            const FormData = require('form-data');
            const formData = new FormData();
            
            // Reconstruct form fields
            for (const [key, value] of Object.entries(req.body || {})) {
              if (value && typeof value === 'object') {
                // File field
                if (value.data) {
                  formData.append(key, Buffer.from(value.data), {
                    filename: value.filename || key,
                    contentType: value.contentType || 'application/octet-stream'
                  });
                } else {
                  formData.append(key, JSON.stringify(value));
                }
              } else {
                formData.append(key, value);
              }
            }
            
            // Use form-data's headers (includes boundary)
            delete fetchOptions.headers['content-type'];
            fetchOptions.body = formData;
            Object.assign(fetchOptions.headers, formData.getHeaders());
          } catch (error) {
            console.error('[Proxy] Error reconstructing FormData:', error);
            // Fallback: try to pass as-is
            fetchOptions.body = req.body;
            fetchOptions.headers['Content-Type'] = contentType;
          }
        }
      } else if (contentType.includes('application/json')) {
        fetchOptions.body = JSON.stringify(req.body);
        fetchOptions.headers['Content-Type'] = 'application/json';
      } else if (req.body) {
        fetchOptions.body = req.body;
      }
    }
    
    console.log(`[Proxy] Making fetch request...`);
    
    // Make request to backend
    const response = await fetch(fullUrl, fetchOptions);
    
    console.log(`[Proxy] Backend response: ${response.status} ${response.statusText}`);
    
    // Get response data
    const contentType = response.headers.get('content-type') || '';
    let data;
    
    if (contentType.includes('application/json')) {
      data = await response.json();
    } else if (contentType.includes('text/')) {
      data = await response.text();
    } else {
      data = await response.arrayBuffer();
    }
    
    // Set response status and headers
    res.status(response.status);
    
    // Copy response headers
    response.headers.forEach((value, key) => {
      const lowerKey = key.toLowerCase();
      if (!['connection', 'transfer-encoding', 'content-encoding'].includes(lowerKey)) {
        res.setHeader(key, value);
      }
    });
    
    // Send response
    if (data instanceof ArrayBuffer) {
      res.send(Buffer.from(data));
    } else {
      res.json(data);
    }
    
    console.log(`[Proxy] Response sent successfully`);
    
  } catch (error) {
    console.error('[Proxy] Error:', error.message);
    console.error('[Proxy] Stack:', error.stack);
    console.error('[Proxy] Full error:', error);
    
    res.status(500).json({
      error: 'Proxy error',
      message: error.message,
      backendUrl: BACKEND_URL,
      requestMethod: req.method,
      requestUrl: req.url
    });
  }
}
