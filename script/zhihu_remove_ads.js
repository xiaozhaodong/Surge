// Surge Script to Remove Ads from Zhihu API Responses

// Define the pattern for matching the Zhihu API request.
const urlPattern = /^https:\/\/api\.zhihu\.com\/questions\/\d+(\/answers|\/feeds|\?include=)/;

// Check if the request URL matches the defined pattern.
if (urlPattern.test($request.url)) {
  // Process the response body to filter out the ads.
  let body = JSON.parse($response.body);

  // Remove the 'ad_info' and 'adjson' fields if they exist.
  delete body.ad_info;
  delete body.adjson;

  // Filter out any embedded ads inside the 'data' field.
  if (body.data) {
    body.data = body.data.filter(item => item.type !== 'ad');
  }

  // Convert the modified object back to JSON string.
  $done({ body: JSON.stringify(body) });
} else {
  // If the request does not match, proceed with the original response.
  $done({});
}
