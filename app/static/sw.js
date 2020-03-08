self.addEventListener("push", function(event) {
    if (event.data) {
        showLocalNotification("Grøn strøm", event.data.text(),  self.registration);
    }
});

const showLocalNotification = (title, body, swRegistration) => {
    const options = {
        body: body,
        icon: "/plug-512.png",
        vibrate: [100, 100],
    };
    swRegistration.showNotification(title, options);
};

// Chrome unfortunately requires a fetch event handler to be in place for an app to be
// considered "installable", even if there is no reason to handle the event. We get around
// this by simply adding a trivial handler.
self.addEventListener('fetch', function() {});