"use strict";

// Websocket used to communicate with the Python server backend
let ws = new WebSocket("ws://" + location.host + "/ws");

// Global to keep track of whether we are filtering out state updates in the
// transcript area so that we only display the command/response when
// user-initiated
let allow_state_transcript = true;

let selected_clip;
let current_state;
let slots = [];
let initial_slot_selected = false
let selected_slot;
let format_token;

// HyperDeck control elements on the HTML page
let body = document.body;
let loading = document.getElementById("loading")
let loop = document.getElementById("loop");
let single = document.getElementById("single");
let speed = document.getElementById("speed");
let speed_val = document.getElementById("speed_val");
let state_refresh = document.getElementById("state_refresh");
let clips = document.getElementById("clips");
let locals = document.getElementById("local-files");
let clips_refresh = document.getElementById("clips_refresh");
let record = document.getElementById("record");
let record_icon = document.getElementById("record-icon");
let play = document.getElementById("play");
let stopEle = document.getElementById("stop");
let prev = document.getElementById("prev");
let next = document.getElementById("next");
let sent = document.getElementById("sent");
let received = document.getElementById("received");
let download = document.getElementById("download");
let del = document.getElementById("delete");
let dispTime = document.getElementById("disp-time");
let dispFormat = document.getElementById("disp-format");
let dispRec = document.getElementById("disp-rec");
let sdNum = document.getElementById("sd-num");
let msgBox = document.getElementById("msg-box");
let settings = document.getElementById("settings");
let autoRecord = document.getElementById("auto-record");
let autoDownload = document.getElementById("auto-download");
let settingsBtn = document.getElementById("settings-btn");
let view = document.getElementById("view");
let info = document.getElementById("info-btn");
let formatBtn = document.getElementById("format");
let formatOpt = document.getElementById("format-options");
let formatConf = document.getElementById("format-confirm");
let exFat = document.getElementById("exFat");
let hfs = document.getElementById("hfs");
let formatYes = document.getElementById("format-yes");
let formatNo = document.getElementById("format-no");
let slotHeader = document.getElementById("current-slot");
let sd1 = document.getElementById("sd-1");
let sd2 = document.getElementById("sd-2");

let messageBoxArray = [];
messageBoxArray.push(msgBox.id, settings.id, formatOpt.id, formatConf.id);

// Bind HTML elements to HyperDeck commands
speed.oninput = function () {
  speed_val.innerHTML = parseFloat(speed.value).toFixed(2);
};

let setLoading = (on) => {
  if (on) {
    loading.style.display = "inline-block"
  } else {
    loading.style.display = "none"
  }
}

let selectDisk = (id) => {
  let command = {
    command: "slot select",
    params: {
      id: id,
    },
  };
  ws.send(JSON.stringify(command));
};

sd1.onclick = () => {
  selectDisk('1')
}

sd2.onclick = () => {
  selectDisk('2')
}

let handleSelectedClip = (clip, disable, cursor) => {
  selected_clip = clip;
  download.disabled = disable;
  del.disabled = disable;
  download.style.cursor = cursor;
  del.style.cursor = cursor;
};

let handleMessageDisplay = (idtext) => {
  for (let m = 0; m < messageBoxArray.length; m++) {
    let tempDoc = document.getElementById(messageBoxArray[m]);
    if (messageBoxArray[m] != idtext) {
      tempDoc.style.display = "none";
    } else {
      tempDoc.style.display = "flex";
    }
  }
};

let msg = (text, action) => {
  handleMessageDisplay(msgBox.id);
  msgBox.innerHTML = '<div class="alert">' + text + "</div>";
  if (action == "close") {
    setTimeout(() => {
      msgBox.innerHTML = "";
    }, 3000);
  }
};
let recordFunc = () => {
  handleSelectedClip("", true, "not-allowed");
  let command = {
    command: "record",
  };
  ws.send(JSON.stringify(command));
};
record.onclick = function () {
  recordFunc();
};
play.onclick = function () {
  let command = {
    command: "play",
    params: {
      loop: loop.checked,
      single: single.checked,
      speed: speed.value,
    },
  };
  ws.send(JSON.stringify(command));
};
let stopFunc = () => {
  let command = {
    command: "stop",
  };
  ws.send(JSON.stringify(command));
};
stopEle.onclick = () => {
  stopFunc();
};
prev.onclick = function () {
  let command = {
    command: "clip_previous",
  };
  ws.send(JSON.stringify(command));
};
next.onclick = function () {
  let command = {
    command: "clip_next",
  };
  ws.send(JSON.stringify(command));
};
let settingsUpdate = () => {
  let command = {
    command: "set_settings",
    params: {
      "auto-record": autoRecord.checked,
      "auto-download": autoDownload.checked,
    },
  };
  ws.send(JSON.stringify(command));
};
autoRecord.onchange = () => {
  settingsUpdate();
};
autoDownload.onchange = () => {
  settingsUpdate();
};

settingsBtn.onclick = () => {
  if (settings.style.display == "none") {
    handleMessageDisplay(settings.id);
  } else {
    handleMessageDisplay(msgBox.id);
  }
};
formatBtn.onclick = () => {
  handleMessageDisplay(formatOpt.id);
};
let formatPrepare = (format) => {
  let command = {
    command: "format",
    params: {
      f: format,
    },
  };
  ws.send(JSON.stringify(command));
};

exFat.onclick = () => {
  formatPrepare("exFat");
};
hfs.onclick = () => {
  formatPrepare("HFS+");
};

let setupFormatConfirm = (token) => {
  handleMessageDisplay(formatConf.id);
  formatYes.onclick = () => {
    formatConfirm(token, true);
  };
  formatNo.onclick = () => {
    formatConfirm(token, false);
  };
};
let formatConfirm = (token, yes) => {
  if (yes) {
    let command = {
      command: "format_confirm",
      params: {
        token: token,
      },
    };
    ws.send(JSON.stringify(command));
  } else {
    msg("Format Cancelled", "close");
  }
};
view.onclick = () => {
  let command = {
    command: "view",
  };
  ws.send(JSON.stringify(command));
};
info.onclick = () => {
  let command = {
    command: "config",
  };
  ws.send(JSON.stringify(command));
};
clips.onchange = function () {
  let command = {
    command: "clip_select",
    params: {
      id: clips.selectedIndex,
    },
  };
  ws.send(JSON.stringify(command));
  handleSelectedClip(clips.value, false, "pointer");
};
let clipRefresh = () => {
  let command = {
    command: "clip_refresh",
  };
  ws.send(JSON.stringify(command));
};
clips_refresh.onclick = function () {
  clipRefresh();
};
let refreshAll = () => {
  let command = {
    command: "refresh",
  };
  ws.send(JSON.stringify(command));
};
let getSettings = () => {
  let command = {
    command: "get_settings",
  };
  ws.send(JSON.stringify(command));
};
ws.onopen = () => {
  refreshAll();
  getSettings();
};

// Websocket message parsing
ws.onmessage = function (message) {
  let data = JSON.parse(message.data);

  switch (data.response) {
    case "read_settings":
      autoRecord.checked = data.params["auto-record"];
      autoDownload.checked = data.params["auto-download"];
      if (data.params["reason"] == "startup") {
        if (data.params["auto-record"] && current_state != "record") {
          recordFunc();
        }
      }
      if (data.params["reason"] == "download") {
        if (data.params["auto-download"]) {
          setTimeout(() => {
            let command = {
              command: "download_latest_clip",
            };
            ws.send(JSON.stringify(command));
          }, 2000); //to prevent over working the web socket
        }
      }
      break;
    
    /*case "clip_count":
      clips.innerHTML = "";
      for (let i = 0; i < data.params["count"]; i++)
        clips.add(new Option("[--:--:--:--] - Clip " + i));
      break;

    case "clip_info":
      clips.options[data.params["id"]].text =
        data.params["name"] + " (" + data.params["duration"] + ")";
      clips.options[data.params["id"]].value = data.params["name"];
      break;*/
    
    case "clip_list":
      clips.innerHTML = ""
      data.params["clips"].forEach((e, k) => {
        clips[k] = new Option(e["name"] + " (" + e["duration"] + ")", e["name"])
      })
      break

    case "status":
      if (data.params["status"] !== undefined) {
        updateHandler(
          data.params["status"],
          data.params["slot id"],
          data.params["input video format"],
          data.params["display timecode"]
        );
      }
      //initially set formatting for disk that was selected before start of program
      if (initial_slot_selected == false) {
        selectDisk(data.params["slot id"])
      }
      initial_slot_selected = true
      break;

    case "transcript":
      // We periodically send transport info requests automatically
      // to the HyperDeck, so don't bother showing them to the user
      // unless this was a manual refresh request.
      let is_state_request = data.params["sent"][0] == "transport info";

      if (allow_state_transcript || !is_state_request) {
        //sent.innerHTML = data.params["sent"].join("\n").trim();
        //received.innerHTML = data.params["received"].join("\n").trim();
        allow_state_transcript = false;
      }
      break;
    
    case "sd_slots":
      slots = data.params["slots"];
      for (let i = 1; i < 3; i++) {
        let card = document.getElementById("sd-" + i.toString());
        if (slots.includes(i.toString())) {
          card.classList.add("sd-full");
          card.classList.remove("sd-empty");
          card.disabled = false;
        } else {
          card.classList.remove("sd-full");
          card.classList.add("sd-empty");
          card.disable = true;
        }
      }
      break;

    case "alert":
      msg(data.params["status"], data.params["action"]);
      break;

    case "get_latest_clip":
      setTimeout(() => {
        let command = {
          command: "download_latest_clip",
        };
        ws.send(JSON.stringify(command));
      }, 2000); //to prevent over working the web socket
      break;

    case "download_clip":
      downloadFunc(data.params["clip"]);
      break;

    case "clip_refresh":
      setTimeout(() => {
        clipRefresh();
      }, 2000); //to prevent over working the web socket
      break;
    
    case "slot_select":
      if (data.params["slot"] == '1') {
        sd1.classList.add("selected-disk")
        sd2.classList.remove("selected-disk")
      }
      if (data.params["slot"] == '2') {
        sd1.classList.remove("selected-disk")
        sd2.classList.add("selected-disk")
      }
      break;
    
    case "format_confirm":
      format_token = data.params["token"];
      setupFormatConfirm(format_token);
      break;
    
    case "loading":
        setLoading(data.params["status"])
      break
  }
};

// Initial control setup once the page is loaded
body.onload = function () {
  speed.value = 1.0;
  speed.oninput();
  //setAutoDownload();
};

let downloadFunc = (sc) => {
  let command = {
    command: "download",
    params: {
      sf: sc,
    },
  };
  ws.send(JSON.stringify(command));
};
download.onclick = () => {
  downloadFunc(selected_clip);
};

del.onclick = () => {
  let command = {
    command: "delete",
    params: {
      sf: selected_clip,
    },
  };
  ws.send(JSON.stringify(command));
  handleSelectedClip("", true, "not-allowed");
};

let updateHandler = (state, sd, format, time) => {
  record_icon.className = "fa-solid fa-circle " + state + "ing";
  dispRec.className = "";
  dispRec.classList.add(state);
  dispTime.innerHTML = time;
  dispFormat.innerHTML = format;
  selected_slot = sd;
  sdNum.innerHTML = sd;
  slotHeader.innerHTML = "Current SD Slot: " + sd;
  current_state = state;
  if (state == "record") {
    document.getElementById("sd-" + sd + "-ind").classList.add("sd-on");
  } else {
    document.getElementById("sd-" + sd + "-ind").classList.remove("sd-on");
  }
};

window.onbeforeunload = () => {
  let command = {
    command: "browser_close",
  };
  ws.send(JSON.stringify(command));
};
