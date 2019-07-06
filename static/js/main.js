var locked = false

function reload() {
    window.location.reload()
}

function resetStats() {
    window.localStorage.setItem("correct", "0");
    window.localStorage.setItem("wrong", "0");
    updateScore()
}

function updateScore() {
    if (!window.localStorage.getItem('correct') || !window.localStorage.getItem('wrong')) {
        resetStats()
    }
    score = window.localStorage.getItem('score')
    num_correct = parseInt(window.localStorage.getItem('correct'));
    num_wrong = parseInt(window.localStorage.getItem('wrong'));
    document.getElementById("num_correct").innerHTML = num_correct;
    document.getElementById("num_wrong").innerHTML = num_wrong;
}


function processClick(correct, id) {
    if (!locked) {
        locked = true
        if (correct) {
            num_correct = parseInt(window.localStorage.getItem('correct'));
            window.localStorage.setItem("correct", num_correct + 1);
        } else {
            num_wrong = parseInt(window.localStorage.getItem('wrong'));
            window.localStorage.setItem("wrong", num_wrong + 1);
        }
        document.getElementById(id).style.background = "#ff4757";
        document.getElementsByClassName("correct")[0].style.background = "#2ed573";
        updateScore()
        setTimeout(reload, 100)
    }
}
