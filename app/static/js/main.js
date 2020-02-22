$(document).ready(function() {
    $.get("/api/v1/current-emission-intensity", function(data) {
      $("#jumbotron").css("background-color", data["intensity-level-color"]);
      $("#intensity-level").text(data["intensity-level"]);
      $("#current-intensity").text(data["current-intensity"]);
      $("#latest-data").text(data["latest-data"]);
      $("#best-hour-start").text(data["best-hour-start"]);
      $("#best-hour-end").text(data["best-hour-end"]);
      $("#best-hour-intensity").text(data["best-hour-intensity"]);
      $("#body").css('visibility', 'visible');;

      var plot_data = data["plot-data"];
      var plot_opt = {"renderer": "canvas", "actions": false};
      vegaEmbed("#vis", plot_data, plot_opt);
    });
});