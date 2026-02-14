/**
 * Node.js Bridge for Website Understanding SDK
 * Reads HTML from stdin, analyzes it, outputs JSON to stdout
 */

import { analyzePage } from './website-understanding-sdk/src/analyzePage.js';
import * as fs from 'fs';

// Read HTML from stdin
let html = '';

process.stdin.setEncoding('utf8');
process.stdin.on('data', (chunk) => {
  html += chunk;
});

process.stdin.on('end', async () => {
  try {
    // Analyze the HTML
    const result = await analyzePage(html, { dynamic: false });

    // Output JSON to stdout
    console.log(JSON.stringify(result, null, 2));
  } catch (error) {
    // Output error as JSON
    console.error(JSON.stringify({
      error: error.message,
      page_type: "unknown",
      sections: [],
      elements: { inputs: [], buttons: [], links: [], images: [] },
      metadata: { title: null, description: null, url: null }
    }));
    process.exit(1);
  }
});
