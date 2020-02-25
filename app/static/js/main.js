$(document).ready(function() {
    $.get("/api/v1/current-emission-intensity", function(data) {
      $("#jumbotron").css("background-color", data["intensity-level-bgcolor"]);
      $("#jumbotron").css("color", data["intensity-level-fgcolor"]);
      $("#info-link").css("color", data["intensity-level-fgcolor"]);
      $(".btn-transparent").css('border-color', data["intensity-level-border-color"]);
      $("#intensity-level").text(data["intensity-level"]);
      $("#current-intensity").text(data["current-intensity"]);
      $("#latest-data").text(data["latest-data"]);
      $("#body").css('visibility', 'visible');
      $(".btn-transparent").css('color', data["intensity-level-fgcolor"]);

      var plot_data = data["plot-data"];
      var plot_opt = {"renderer": "canvas", "actions": false};
      vegaEmbed("#vis", plot_data, plot_opt);
    });
    $.get("/api/v1/greenest-hour/1/12", function(data) {
      $("#best-hour-start").text(data["best-hour-start"]);
      $("#best-hour-end").text(data["best-hour-end"]);
      $("#best-hour-intensity").text(data["best-hour-intensity"]);
    });
});

$(".dropdown-menu>a").on('click', function() {
    var selText = $(this).text();
    console.log(selText);
    $(this).parent('.dropdown-menu').siblings('.dropdown-toggle').html(selText);
    $(this).parent('.dropdown-menu').siblings('.dropdown-toggle').data('value', $(this).data('value'));
    var period = $('#dropdown-toggle-period').data('value');
    var horizon = $('#dropdown-toggle-horizon').data('value');
    if (period > 1) {
        $('#de-den').html("De");
    } else {
        $('#de-den').html("Den");
    }
    $.get("/api/v1/greenest-hour/" + period + "/" + horizon, function(data) {
      $("#best-hour-start").text(data["best-hour-start"]);
      $("#best-hour-end").text(data["best-hour-end"]);
      $("#best-hour-intensity").text(data["best-hour-intensity"]);
    });
});