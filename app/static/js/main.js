function updateGreenestPeriod() {
    // Update all data pertaining to the "greenest period of time"
    var period = $('#dropdown-toggle-period').data('value');
    var horizon = $('#dropdown-toggle-horizon').data('value');
    $.get("/api/v1/greenest-period/" + period + "/" + horizon, function(data) {
        $("#current-intensity").text(data["current-intensity"]);
        $("#improvement").text(data["improvement"]);
        $("#best-period-start").text(data["best-period-start"]);
        $("#best-period-end").text(data["best-period-end"]);
        $("#best-period-intensity").text(data["best-period-intensity"]);
    });
}

function updateEmissionIntensity() {
    // Update the main information about emission intensities, and the corresponding plot.
    $.get("/api/v1/current-emission-intensity", function(data) {
        $("#jumbotron").css("background-color", data["intensity-level-bgcolor"]);
        $("meta[name='theme-color']").attr("content", data["intensity-level-bgcolor"]);
        $("meta[name='msapplication-navbutton-color']").attr("content", data["intensity-level-bgcolor"]);
        $("meta[name='apple-mobile-web-app-status-bar-style']").attr("content", data["intensity-level-bgcolor"]);
        $("#jumbotron").css("color", data["intensity-level-fgcolor"]);
        $("#info-link").css("color", data["intensity-level-fgcolor"]);
        $(".btn-transparent").css('border-color', data["intensity-level-border-color"]);
        $("#intensity-level").text(data["intensity-level"]);
        $("#latest-data").text(data["latest-data"]);
        $("#body").css('visibility', 'visible');
        $(".btn-transparent").css('color', data["intensity-level-fgcolor"]);
        // A priori, we allow selections of 6, 12, and 24 hours in the horizon dropdown, but if
        // our current forecast is shorter than that, we update the values accordingly. Note that
        // we do not have to update the actual data properties themselves, as the API will simply
        // ignore the fact that the desired horizon might be longer than the available forecast.
        var length = data["forecast-length-hours"];
        var selectedHorizon = $('#dropdown-toggle-horizon').data('value');
        if (length <= 12) {
            var newText = length + " timer";
            $("#dropdown-12-hours").html(newText);
            $("#dropdown-24-hours").css('visibility', 'collapse');
            if (selectedHorizon == 12) {
                $('#dropdown-toggle-horizon').html(newText);
            }
        } else if (length < 24) {
            $("#dropdown-24-hours").html(length + " timer");
            if (selectedHorizon == 24) {
                $('#dropdown-toggle-horizon').html(newText);
            }
        }

        // TODO: Rather than generating the plot from scratch, it would make sense to keep the
        // Vega-Lite specification static, and then simply update its data here.
        var plot_data = data["plot-data"];
        var plot_opt = {"renderer": "canvas", "actions": false};
        vegaEmbed("#vis", plot_data, plot_opt);
    });
}

function updateAll() {
    // Update all dynamic data on the page.
    updateEmissionIntensity();
    updateGreenestPeriod();
}

$(document).ready(function() {
    // Immediately set the page data, and refresh it every five minutes.
    updateAll();
    setInterval(updateAll, 5*60*1000);
    registerServiceWorker();

    // Determine which "Add to home screen" guides to display based on user agents.
    var ua = navigator.userAgent.toLowerCase();
    var isiOS = !!navigator.platform && /iPad|iPhone|iPod/.test(navigator.platform);
    var isChrome = ua.indexOf('chrome') > -1 && ua.indexOf('edg') == -1;
    if (!isiOS && ua.indexOf('android') == -1)
        $("#not-android-ios-guide").css('display', 'inherit');
    if (ua.indexOf('firefox') > -1 && ua.indexOf('android') > -1)
        $("#firefox-android-guide").css('display', 'inherit');
    if (ua.indexOf('fxios') > -1)
        $("#firefox-ios-guide").css('display', 'inherit');
    if (ua.indexOf('crios') > -1)
        $("#chrome-ios-guide").css('display', 'inherit');
    if (ua.indexOf('safari') > -1 && isiOS)
        $("#safari-ios-guide").css('display', 'inherit');

    if (navigator && navigator.serviceWorker) {
        navigator.serviceWorker.ready.then(function (reg) {
            if (reg.pushManager) {
                // By restricting to browsers whose registration has a pushManager, we effectively
                // only support Firefox and Chrome, simply because Safari doesn't follow the spec.
                // Hopefully, in time, they will.
                $("#settings").css('display', 'inherit');
                // Ensure that the "Få daglig opdatering" checkbox is disabled, if we are not
                // currently subscribing to push messages.
                reg.pushManager.getSubscription().then(function(sub) {
                    if (sub == null) {
                        $('#toggle-notification').prop('checked', sub != null).change();
                    }
                });
            }
        });
    
    }
});

$('#toggle-notification').change(function() {
    if ($(this).prop('checked')) {
        window.Notification.requestPermission().then(function (permission) {
            // TODO: Provide feedback in case permission is not granted; this can happen if the user revoked the permission
            // after having subscribed once, and in that case, the only way to regrant permission in e.g. Firefox and
            // Chrome on Android is through the user agent's settings; that's poor UX.
            if (permission === 'granted') {
                // Use the VAPID keys generated out of band. The corresponding private key will be used by the service
                // responsible for actually pushing messages.
                var applicationServerKey = urlB64ToUint8Array(
                    'BOhO7gueTjZ60EP0lxuR2-kmq1WqbenyPgq1ZWvINPG86uh8C0ssn5XM72ranRIrI1r0lNiK7GV4rIaUcj5HJns'
                )
                var options = { applicationServerKey: applicationServerKey, userVisibleOnly: true }
                navigator.serviceWorker.ready.then(function(reg)
                {
                    reg.pushManager.subscribe(options).then(function(subscription) {
                        saveSubscription(subscription)
                    })
                })
            }
        })
    } else {
        navigator.serviceWorker.ready.then(function(reg) {
            reg.pushManager.getSubscription().then(function(subscription) {
                if (subscription) {
                    subscription.unsubscribe().then(function(successful) {
                        removeSubscription(subscription)
                    }).catch(function(e) {
                        // TODO: Handle errors
                    })
                }
            })        
        });
    }
}) 

// Besides updating page data every five minutes, we also update it on the window 'focus' event. This
// is necessary to ensure updates when users have added the page to their phone/tablet home screen, in
// which case they might otherwise end up with stale data that can go for up to five minutes without updates.
$(window).on('focus', function() { updateAll(); });

$(".dropdown-menu>a").on('click', function() {
    // Get the text of the selected item and replace the dropdown contents with it.
    var selText = $(this).text();
    var dropdownToggle = $(this).parent('.dropdown-menu').siblings('.dropdown-toggle')
    dropdownToggle.html(selText);
    if (dropdownToggle[0].id == "dropdown-toggle-period") {
        $('#hours').html(selText);
    }
    // We use data properties to keep track of the value of the selected item. This allows us to perform
    // the actual update without relying on view-specific properties. If we get much more of this sort of
    // logic, jumping to a more heavy-weight JavaScript framework will make sense.
    dropdownToggle.data('value', $(this).data('value'));
    // Update the grammar on the web page; if we go from 1 hour to 2 hours, we want "den grønneste time" to
    // become "de grønneste timer".
    var period = $('#dropdown-toggle-period').data('value');
    if (period > 1) {
        $('#de-den-upper').html("De");
        $('#de-den-lower').html("de");
    } else {
        $('#de-den-upper').html("Den");
        $('#de-den-lower').html("den");
    }
    updateGreenestPeriod();
});


function registerServiceWorker() {
    if (navigator && navigator.serviceWorker) {
        navigator.serviceWorker.register('/sw.js')
    }
}

// urlB64ToUint8Array is a magic function that will encode the base64 public key
// to Array buffer which is needed by the subscription option
function urlB64ToUint8Array(base64String) {
    var padding = '='.repeat((4 - (base64String.length % 4)) % 4)
    var base64 = (base64String + padding).replace(/\-/g, '+').replace(/_/g, '/')
    var rawData = atob(base64)
    var outputArray = new Uint8Array(rawData.length)
    for (let i = 0; i < rawData.length; ++i) {
        outputArray[i] = rawData.charCodeAt(i)
    }
    return outputArray
}

function saveSubscription(subscription) {
    fetch('/api/v1/save-subscription', {
        method: 'post',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify(subscription),
    }).then(function(response) {
        return response.json()
    });
}

function removeSubscription(subscription) {
    fetch('/api/v1/remove-subscription', {
        method: 'post',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify(subscription),
    }).then(function(response) {
        return response.json()
    })
}

// Installation logic currently just used to provide an "install" button on Chrome for Android.
// This particular pattern is taken verbatim from the MDN example at https://mdn.github.io/pwa-examples/a2hs/
let deferredPrompt;

window.addEventListener('beforeinstallprompt', function(e) {
    // Prevent Chrome 67 and earlier from automatically showing the prompt
    e.preventDefault();
    // Stash the event so it can be triggered later.
    deferredPrompt = e;
    // Update UI to notify the user they can add to home screen
    var ua = navigator.userAgent.toLowerCase();
    if (ua.indexOf('android') > -1) {
        $('#chrome-android-guide').css('display', 'block');
    } else {
        $('#chrome-desktop-guide').css('display', 'block');
    }

    $('.install-button').click(function(e) {
        // Hide our user interface that shows our A2HS button
        var ua = navigator.userAgent.toLowerCase();
        if (ua.indexOf('android') > -1) {
            $('#chrome-android-guide').css('display', 'none');
        } else {
            $('#chrome-desktop-guide').css('display', 'none');
        }
        // Show the prompt
        deferredPrompt.prompt();
        // Wait for the user to respond to the prompt
        deferredPrompt.userChoice.then(function(choiceResult) {
            deferredPrompt = null;
        });
    });
});
