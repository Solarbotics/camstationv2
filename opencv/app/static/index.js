(function () {
    "use strict";

    function submit_threshold() {
      let form = document.getElementById("configOptions")
      // console.log(form);
      fetch(
        "/config", {
          method: "POST",
          headers: {
            "Content-Type": "application/json"
          },
          body: JSON.stringify({threshold: form.elements["threshold"].value}),
        }
      ).finally(function () {
        // form.reset();
      })
    }

    let configOptions = document.getElementById("configOptions")
    configOptions.addEventListener("input", function (event) {
      let form = document.getElementById("configOptions");
      form.elements["thresholdOutput"].value = form.elements["threshold"].value;
      submit_threshold();
    });
    // console.log(configOptions);
    configOptions.addEventListener("submit", function (event) {
      // console.log(event);
      event.preventDefault();
      submit_threshold();
      return false
    });

    function repeat(func, times, delay) {
      func(times);
      if (times > 0) {
        setTimeout(() => repeat(func, times - 1, delay), delay);
      }
    }

    let snapshotButton = document.getElementById("snapshot");
    snapshotButton.addEventListener("click", function (event) {
      repeat(function (index) {
        fetch("/snap", {
          method: "POST"
        }).then(function (response) {
          response.text().then(text => document.getElementById("snapshotResult").textContent = text);
          snapshotButton.classList.add("outline");
          setTimeout(() => snapshotButton.classList.remove("outline"), 1000);
        })
      }, 10, 15000);
    });

    let lightsInput = document.getElementById("lightsLevel")
    lightsInput.addEventListener("input", function (event) {
      fetch(
        "/lights", {
          method: "POST",
          headers: {
            "Content-Type": "application/json"
          },
          body: JSON.stringify({level: lightsInput.value}),
        }
      )
    });

    // let photoButton = document.getElementById("photos");
    // photoButton.addEventListener("click", function (event) {
    //   fetch("/photos", {
    //     method: "POST"
    //   });
    // })
    
    // Construct a query function to be bound to an event such as click.
    // Executing the returned function:
    // Calls prep
    // Sends an <action> request to /<name>,
    // Calls callback on the text of the response from /<name>
    let query = function (name, action, prep, callback) {
      let func = function (event) {
        prep();
        fetch("/" + name, {
          method: action
        }).then(function (response) {
          response.text().then(callback);
        })
      };
      return func;
    }


    // Take an html element and construct a function
    // that takes a single parameter and copies it
    // into the text content of the element
    let write_on = function(output) {
      let func = function (text) {
        output.textContent = text;
      }
      return func;
    }

    let update_on = function (output) {
      let func = function (text) {
        text = text + " (" + String(Date.now()) + ")";
        write_on(output)(text);
      }
      return func;
    }

    // Collect elements
    let activateAction = document.getElementById("activateAction");
    let activateButton = activateAction.children[0];
    let activateInfo = activateAction.children[1];

    // Define handling function
    let activate_function = function (output) {
      // The actual function that uses the provided output
      let func = function (text) {
        let data = JSON.parse(text);
        let gallery = document.getElementById("photosGallery");
        gallery.replaceChildren();
        for (const image_data of data["photos"]) {
          let image = document.createElement("img");
          image.setAttribute("src", "data:image/jpeg;base64," + image_data);
          gallery.appendChild(image)
        }
        output.textContent = (
          "Size: " + data["size"]
          + ", weight: " + data["weight"]
          + ", height: " + data["height"]
          + "."
        );
      }
      return func;
    }; 
    // activateButton.addEventListener("click", function (event))
    // Bind query function
    activateButton.addEventListener(
      "click",
      query("activate", "POST", (() => write_on(activateInfo)("Working...")), activate_function(activateInfo))
    );

    // Setup 'actions'.
    // Each action is a div containing a button for input
    // and a span for output.
    // Pressing the button submits a POST request to the endpoint
    // identified by the 'name' attribute of the row.
    let actions = document.getElementsByClassName("action")
    const COLOR_TIME = 500;
    for (const action of actions) {
      let button = action.children[0];
      let output = action.children[1];
      let httpMethod = action.getAttribute("action");
      if (httpMethod === null) {
        httpMethod = "POST";
      }
      button.addEventListener("click", query(
        action.getAttribute("name"),
        httpMethod,
        function () {
          button.classList.add("working-button");
        },
        function () {
          button.classList.remove("working-button");
          button.classList.add("finished-button");
          setTimeout(() => button.classList.remove("finished-button"), COLOR_TIME);
        }
      ));
    }

    // Setup polling
    function start_polling(name, method) {

      const GAP = 1000;

      if (method === undefined) {
        method = "GET";
      }

      let span = document.getElementById(name);
      function update() {
        let start = Date.now();
        fetch("/" + name, {method: method}).then(function (response) {
          response.text().then(
            write_on(span)
          ).then(function (value) {
            setTimeout(update, Math.max(0, GAP - (Date.now() - start)));
          })
        });
      }
      // Start polling
      setTimeout(update, 0);

    }

    let start = document.getElementById("start");
    start.addEventListener("click", function () {
      start_polling("weight");
      start_polling("height");
      start_polling("bounds");
    });

})();
