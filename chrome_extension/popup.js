document.getElementById('processButton').addEventListener('click', async () => {
  const statusDiv = document.getElementById('status');
  statusDiv.textContent = 'Processing...';

  try {
    // Get the current active tab
    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
    const url = tab.url;

    // Send to local API
    const response = await fetch('http://localhost:8000/process', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({ url: url })
    });

    if (response.ok) {
      statusDiv.textContent = 'Success! Check your local folder.';
      statusDiv.style.color = 'green';
    } else {
      statusDiv.textContent = 'Error: ' + response.statusText;
      statusDiv.style.color = 'red';
    }
  } catch (error) {
    statusDiv.textContent = 'Failed to connect to API. Is Docker running?';
    statusDiv.style.color = 'red';
    console.error(error);
  }
});
