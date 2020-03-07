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
