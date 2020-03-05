self.addEventListener('activate', async () => {
  // This will be called only once when the service worker is activated.
  try {
    console.log('activating')
  } catch (err) {
    console.log('Error', err)
  }
})

self.addEventListener("push", function(event) {
  if (event.data) {
    console.log("Push event!! ", event.data.text());
    showLocalNotification("Grøn strøm", event.data.text(),  self.registration);
  } else {
    console.log("Push event but no data");
  }
});

const showLocalNotification = (title, body, swRegistration) => {
  const options = {
    body: body,
    icon: "/plug-512.png",
    vibrate: [100,100],
    // here you can add more properties like icon, image, vibrate, etc.
  };
  swRegistration.showNotification(title, options);
};
