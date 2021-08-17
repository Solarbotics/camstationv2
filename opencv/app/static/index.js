(function () {
    "use strict";

    function sleep(ms) {
      return new Promise(resolve => setTimeout(resolve, ms));
    }

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

    let last_lights_level = 0;
    let lightsForm = document.getElementById("lights");
    lightsForm.addEventListener("input", function (event) {

      let value;
      if (lightsForm.elements["enabled"].checked) {
        value = lightsForm.elements["value"].value;
      } else {
        value = 0;
      }

      if (value != last_lights_level) {
        last_lights_level = value;
        fetch(
          "/lights", {
            method: "POST",
            headers: {
              "Content-Type": "application/json"
            },
            body: JSON.stringify({level: value}),
          }
        )
      }
      
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
        }).then(callback)
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

    let fill_gallery = function(photos) {
      let gallery = document.getElementById("photosGallery");
      gallery.replaceChildren();
      for (const image_data of photos) {
        let image = document.createElement("img");
        image.setAttribute("src", "data:image/jpeg;base64," + image_data);
        gallery.appendChild(image)
      }
    }

    function setup_actions(handlers) {

      // Setup 'actions'.
      // Each action is a div containing a button for input
      // and a span for output.
      // Pressing the button submits a POST request to the endpoint
      // identified by the 'name' attribute of the row.
      let actions = document.getElementsByClassName("action");
      const COLOR_TIME = 500;
      for (const action of actions) {
        let button = action.children[0];
        let output = action.children[1];
        let httpMethod = action.getAttribute("action");
        if (httpMethod === null) {
          httpMethod = "POST";
        }
        let name = action.getAttribute("name");
        button.addEventListener("click", query(
          name,
          httpMethod,
          function () {
            button.classList.add("working");
          },
          function (response) {
            button.classList.remove("working");
            button.classList.add("finished");
            // call handler
            if (handlers.hasOwnProperty(name)) {
              handlers[name](response);
            }
            setTimeout(() => button.classList.remove("finished"), COLOR_TIME);
          }
        ));
      }

    }

    // Collect elements
    let activateInfo = document.getElementById("activateAction").children[1];

    // Define handling function
    let activate_function = function (output) {
      // The actual function that uses the provided output
      let func = async function (response) {
        let data = await response.json()
        fill_gallery(data["photos"])
        output.textContent = (
          "Size: " + data["size"]
          + ", weight: " + data["weight"]
          + ", height: " + data["height"]
          + "."
        );
      }
      return func;
    }; 

    const action_handlers = {
      "photos": function (response) {
        console.log("handling photos");
        response.json().then(function (data) {
          fill_gallery(data["photos"])
        })
      },
      "activate": activate_function(activateInfo),
    }
    setup_actions(action_handlers);

    let polling;

    // Setup polling
    function start_polling_data(endpoint, names) {

      const GAP = 1000;
      const method = "GET";

      document.getElementById("control").classList.add("working");
      polling = true;

      async function update() {
        while (polling) {
          let start = Date.now();
          let response = await fetch(endpoint, {method: method})
          let data = await response.json()
          for (const name of names) {
            let span = document.getElementById(name);
            write_on(span)(data[name])
          }
          await sleep(Math.max(0, GAP - (Date.now() - start)))
        }
      }
      update();

    }

    let start = document.getElementById("start");
    start.addEventListener("click", function () {
      start_polling_data("/data", ["weight", "height", "bounds"]);
    });

    let stop = document.getElementById("stop");
    stop.addEventListener("click", function () {
      document.getElementById("control").classList.remove("working");
      polling = false;
    });

    let queryForm = document.getElementById("query");
    queryForm.addEventListener("submit", function (event) {
      // queryForm.elements["query"].value = "";
      queryForm.elements["query"].select();
      fetch(
        config.lookup + "/lookup.html?query=" + queryForm.elements["query"].value,
        {method: "GET"}
      ).then(function (response) {
        let output = document.getElementById("queryResult");
        response.text().then(text => output.innerHTML = text);
      });
      event.preventDefault();
      return false;
    })

})();
