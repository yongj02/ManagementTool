/*
Manages local storage for the program. This remembers which task, team member
and sprint IDs have been selected in their respective tables, so that 
we can remember them while switching between pages.
*/

this_url = window.location.href;
let skipRows = 3;

let currentPage;
let table_offset = 0;

// Sprint tables have more rows than others
// determine the current page based on the url
if (this_url.search("/sprints") > -1){
    skipRows = 4;
    currentPage = "sprint";
} else if (this_url.search("/team") > -1){
    currentPage = "member";
    table_offset = 1;
} else if (this_url.search("/backlog") > -1){
    currentPage = "task";
    table_offset = 1;
}


storage = window.localStorage;

$(document).ready(() => {
    // once the DOM is loaded display the active row and add event listeners to all visible rows
    displayActiveTable();
    addClickListeners();
});

function deleteSaved() {
    // Removes the saved currently open table items
    storage.setItem("task", 0);
    storage.setItem("member", 0);
    storage.setItem("sprint", 0);
}

function hideRow(rowNum){
    rows = $('table').find('tr').slice(rowNum + 1, rowNum + skipRows);
    rows.hide();
}

function showRow(rowNum){
    rows = $('table').find('tr').slice(rowNum + 1, rowNum + skipRows);
    rows.show()
}

function toggleRow(rowNum){
    // toggles the row, and saves its state to storage
    rows = $('table').find('tr').slice(rowNum + 1, rowNum + skipRows);
    rows.toggle();
    if (storage.getItem(currentPage) == rowNum){
        storage.setItem(currentPage, 0);
    } else {
        storage.setItem(currentPage, rowNum);
    }
}

function toggleOnlyRow(event){
    rowNum = event.data;
    // displays the provided row and hides all others
    for (let i = 1; i < $('table').find('tr').length; i += skipRows){
        if (i != rowNum){
            hideRow(i);
        } else {
            toggleRow(i);
        }
    }
}

function addClickListeners(){
    // Add onclick listeners to all table rows to display the hidden
    // rows when they are clicked
    for (let i = 1; i < $('table').find('tr').length; i += skipRows){
        row = $('table').find('tr:nth-of-type(' + (table_offset + i) + ')');
        row.on("click", "tr:not(button)", i, toggleOnlyRow);
    }
}

function displayActiveTable(){
    // Gets the currently active sprint from localStorage, and 
    // toggles it to be displayed in its table
    activeRowNum = storage.getItem(currentPage);
    // hide every row except this one
    for(let i = 1; i < $('table').find('tr').length; i += skipRows){
        if (i != activeRowNum){
            // hide all non active rows
            hideRow(i);
        } else {
            // the row is active
            showRow(i);
        }
    }
}