(function () {
    "use strict";

    // Async function to async sleep for specified milliseconds
    function sleep(ms) {
        return new Promise(resolve => setTimeout(resolve, ms));
    }

    // Function that sends a post request based on the config form fields
    function submit_threshold() {
        let form = document.getElementById("configOptions")
        fetch(
            "/config", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({ threshold: form.elements["threshold"].value }),
        }
        ).finally(function () {
            // form.reset();
        })
    }

    // Add listeners to config form
    let configOptions = document.getElementById("configOptions")
    configOptions.addEventListener("input", function (event) {
        let form = document.getElementById("configOptions");
        form.elements["thresholdOutput"].value = form.elements["threshold"].value;
        submit_threshold();
    });
    configOptions.addEventListener("submit", function (event) {
        event.preventDefault();
        submit_threshold();
        return false
    });

    // repeat(func, n, delay) that calls the first parameter n times;
    // with a minimum of delay time between call starts
    function repeat(func, times, delay) {
        func(times);
        if (times > 0) {
            setTimeout(() => repeat(func, times - 1, delay), delay);
        }
    }

    // Snapshot button that will hit the /snap endpoint
    // a number of times
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

    // We post a new lights level whenever it changes;
    // however the slider is multiplied by the checkbox
    // so if unchecked the level is always 0
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
                body: JSON.stringify({ level: value }),
            }
            )
        }

    });

    // Construct a query function to be bound to an event such as click.
    // Executing the returned function:
    // Calls prep, and uses the return of prep as the JSON body of the request
    // Sends an <action> request to /<name>,
    // Calls callback on the text of the response from /<name>
    let query = function (name, action, prep, callback) {
        let func = function (event) {
            let data = prep();
            // GET/HEAD can't have a body
            if (action === "GET" || action === "HEAD") {
                fetch("/" + name, {
                    method: action,
                }).then(callback)
            } else {
                fetch("/" + name, {
                    method: action,
                    headers: {
                        "Content-Type": "application/json",
                    },
                    body: JSON.stringify(data),
                }).then(callback)
            }
        };
        return func;
    }


    // Take an html element and construct a function
    // that takes a single parameter and copies it
    // into the text content of the element
    let write_on = function (output) {
        let func = function (text) {
            output.textContent = text;
        }
        return func;
    }

    // Curried function that writes text as well as a timestamp on the output
    let update_on = function (output) {
        let func = function (text) {
            text = text + " (" + String(Date.now()) + ")";
            write_on(output)(text);
        }
        return func;
    }

    // Replace the gallery of photos with photos
    // from the base64 encoded parameters
    let fill_gallery = function (photos) {
        let gallery = document.getElementById("photosGallery");
        gallery.replaceChildren();
        for (const image_data of photos) {
            let image = document.createElement("img");
            image.setAttribute("src", "data:image/jpeg;base64," + image_data);
            gallery.appendChild(image)
        }
    }

    // Setup 'actions'.
    // Each action is a div containing a button for input
    // and a span for output.
    // Pressing the button submits a POST (or other if specified)
    // request to the endpoint
    // identified by the 'name' attribute of the row.
    function setup_actions(gatherers, handlers) {
        let actions = document.getElementsByClassName("action");
        const COLOR_TIME = 500;
        for (const action of actions) {
            let button = action.children[0];
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
                    let data;
                    if (gatherers.hasOwnProperty(name)) {
                        data = gatherers[name]();
                    } else {
                        data = {};
                    }
                    return data;
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

    // Function that takes obtained data and displays it on the page
    let dataResult = document.getElementById("dataResult");

    let display_data = function (data) {
        if (data["valid"]) {
            dataResult.textContent = (
                "Size: " + data["size"]
                + ", weight: " + data["weight"]
                + ", height: " + data["height"]
                + ", time: " + data["time"]
                + "."
            );
        } else {
            dataResult.textContent = "No saved data found."
        }
    }

    let display_photos = function (data) {
        if (data["valid"]) {
            fill_gallery(data["photos"]);
        } else {
            fill_gallery([]);
        }
    }

    let update_device_list = function (devices) {
        let deviceSelector = document.getElementById("deviceSelect");
        deviceSelector.innerHTML = "";
        for (const deviceName of devices) {
            let option = document.createElement("option");
            option.textContent = deviceName;
            option.value = deviceName;
            deviceSelector.appendChild(option);
        }
    }

    function writeMountResult(response) {
        response.json().then(function (data) {
            console.log("did mounting stuff");
            console.log(data["message"])
            write_on(document.getElementById("mountResult"))(data["message"]);
        });
    }

    let activateInfo = dataResult;

    // Define handling function
    let activate_function = function (output) {
        // The actual function that uses the provided output
        let func = async function (response) {
            let data = await response.json()
            display_data(data);
            display_photos(data);
        }
        return func;
    };

    // Function that collects the current ILC
    let get_query = function () {
        let data = {
            "query": document.getElementById("ilc").value,
        }
        return data;
    }

    let get_mount_device = function () {
        let data = {
            "device": document.getElementById("deviceSelect").value,
        }
        return data;
    }

    let get_export_device = function () {
        let data = {
            "device": document.getElementById("exportDevice").value,
        };
        return data;
    }

    let gather_info = function () {
        let data = get_query();
        let heightOverride = document.getElementById("heightOverride");
        let heightOverrideValue;
        if (heightOverride.children[1].checked) {
            heightOverrideValue = heightOverride.children[0].value;
        } else {
            heightOverrideValue = null;
        }
        data["height_override"] = heightOverrideValue;
        return data;
    }

    const action_gatherers = {
        "activate": gather_info,
        "photos": get_query,
        "grab_data": gather_info,
        "mount_device": get_mount_device,
        "unmount_device": get_mount_device,
        "export": get_mount_device,
    };

    const action_handlers = {
        "photos": function (response) {
            response.json().then(function (data) {
                display_photos(data)
            })
        },
        "grab_data": function (response) {
            response.json().then(function (data) {
                display_data(data);
            })
        },
        "activate": function (response) {
            response.json().then(function (data) {
                display_data(data);
                display_photos(data);
            })
        },
        "block_devices": function (response) {
            response.json().then(function (data) {
                update_device_list(data["devices"]);
            });
        },
        "mount_device": writeMountResult,
        "unmount_device": writeMountResult,
    };

    setup_actions(action_gatherers, action_handlers);

    // Function that updates the tooltip indicating the ILC being used.
    function updateActivateTooltip(text) {
        let activateButton = document.getElementById("activateButton");
        activateButton.title = text;
    }
    updateActivateTooltip("ILC: None");

    let polling;

    // Setup polling
    function start_polling_data(endpoint, names) {

        const GAP = 200;
        const method = "GET";

        document.getElementById("control").classList.add("working");
        polling = true;

        async function update() {
            while (polling) {
                let start = Date.now();
                let response = await fetch(endpoint, { method: method })
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

    // Buttons to start and stop polling
    let start = document.getElementById("start");
    start.addEventListener("click", function () {
        start_polling_data("/data", ["weight", "height", "bounds"]);
    });

    let stop = document.getElementById("stop");
    stop.addEventListener("click", function () {
        document.getElementById("control").classList.remove("working");
        polling = false;
    });

    // Allow querying the AC Lookup tool
    let queryForm = document.getElementById("query");
    queryForm.addEventListener("submit", function (event) {
        queryForm.elements["query"].select();
        fetch(
            config.lookup + "/check?query=" + queryForm.elements["query"].value,
            { method: "GET" }
        ).then(function (response) {
            let output = document.getElementById("queryResult");
            let ilc;
            response.json().then(function (data) {
                if (data["data"].length > 0) {
                    ilc = data["data"][0]["ItemLookupCode"];
                } else {
                    ilc = queryForm.elements["query"].value;
                }
                output.innerHTML = data["table"];
            }).catch(function (reason) {
                ilc = queryForm.elements["query"].value;
                output.textContent = "Lookup failed."
            }).finally(function () {
                updateActivateTooltip("ILC: " + ilc);
                document.getElementById("ilc").value = ilc;
                queryForm.elements["query"].select();
                fetch(
                    "/saved?ilc=" + ilc,
                    { method: "GET" }
                ).then(async function (response) {
                    let saved_data = await response.json();
                    display_data(saved_data);
                    display_photos(saved_data);
                })
            });
        });
        event.preventDefault();
        return false;
    })

    // Any elements (i.e. buttons) marked with the 'clear-next' class
    // get behaviour added to them that causes
    // the next sibling to be cleared when the button is clicked
    function setup_clearButtons() {
        let clearButtons = document.getElementsByClassName("clear-next");
        for (const button of clearButtons) {
            button.addEventListener("click", function () {
                button.nextElementSibling.innerHTML = "";
            })
        }
    }
    setup_clearButtons();

    // Click refresh button
    document.getElementById("refreshDevices").children[0].click();

})();
