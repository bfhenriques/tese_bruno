$(document).ready(function () {
    //Helper function to keep table row from collapsing when being sorted
    var fixHelperModified = function (e, tr) {
        var $originals = tr.children();
        var $helper = tr.clone();
        $helper.children().each(function (index) {
            $(this).width($originals.eq(index).width())
        });
        return $helper;
    };

    //Make diagnosis table sortable
    $("#add_table tbody").sortable({
        helper: fixHelperModified,
        stop: function (event, ui) {
            renumber_table('#diagnosis_list')
        }
    }).disableSelection();

    //Delete button in table rows
    $('table').on('click', '.btn-delete', function () {
        tableID = '#' + $(this).closest('table').attr('id');
        r = confirm('Delete this item?');
        if (r) {
            $(this).closest('tr').remove();
            renumber_table(tableID);
        }
    });
    populate();

});

//Renumber table rows
function renumber_table(tableID) {
    $(tableID + " tr").each(function () {
        count = $(this).parent().children().index($(this)) + 1;
        $(this).find('.priority').html(count);
    });
}

function addTimeline() {
    var selected = document.getElementById("view_dropdown");

    timelines_json = all_timelines.replace(/&quot;/ig, '"');
    var jsonData = JSON.parse(timelines_json);

    for (var i = 0; i < jsonData.data.length; i++) {
        var timeline = jsonData.data[i];
        if (timeline.pk.toString() === selected.options[selected.selectedIndex].value) {
            var contents = "";
            for(var k=0; k<timeline.contents.length; k++){
                contents += timeline.contents[k].name + " ";
            }
            $(add_table).find('tbody').append('' +
                '<tr>\n' +
                '                        <td><input type="hidden" class="form-control" name="pks" value="' + timeline.pk + '"></td>' +
                '                        <td>' + timeline.name + '</td>\n' +
                '                        <td>' + timeline.duration + '</td>\n' +
                '                        <td>' + timeline.creator + '</td>\n' +
                '                        <td>' + contents + '</td>\n' +
                '                        <td>' + timeline.creation_date + '</td>\n' +
                '                        <td>' + timeline.last_modified + '</td>\n' +
                '                        <td><a class="btn btn-default btn-sm" onclick="deleteTimelineRow(this)">\n' +
                '                          <span class="glyphicon glyphicon-plus" aria-hidden="true"></span><svg data-feather="trash-2"></svg>\n' +
                '                        </a></td>\n' +
                '                    </tr>');
            feather.replace();
            break;
        }
    }

}

function deleteTimelineRow(btn) {
    var row = btn.parentNode.parentNode;
    row.parentNode.removeChild(row);
}

function populate() {
    var dropdown = document.getElementById("view_dropdown");

    table = table_timelines.replace(/&quot;/ig, '"');
    var tableJsonData = JSON.parse(table);

    all = all_timelines.replace(/&quot;/ig, '"');
    var allJsonData = JSON.parse(all);

    $("#add_table tbody tr").remove();
    for (var i = 0; i < tableJsonData.data.length; i++) {
        var timeline = tableJsonData.data[i];
        var contents = "";
        for(var k=0; k<timeline.contents.length; k++){
            contents += timeline.contents[k].name + " ";
        }
        $(add_table).find('tbody').append('' +
                '<tr>\n' +
                '                        <td><input type="hidden" class="form-control" name="pks" value="' + timeline.pk + '"></td>' +
                '                        <td>' + timeline.name + '</td>\n' +
                '                        <td>' + timeline.duration + '</td>\n' +
                '                        <td>' + timeline.creator + '</td>\n' +
                '                        <td>' + contents + '</td>\n' +
                '                        <td>' + timeline.creation_date + '</td>\n' +
                '                        <td>' + timeline.last_modified + '</td>\n' +
                '                        <td><a class="btn btn-default btn-sm" onclick="deleteTimelineRow(this)">\n' +
                '                          <span class="glyphicon glyphicon-plus" aria-hidden="true"></span><svg data-feather="trash-2"></svg>\n' +
                '                        </a></td>\n' +
                '                    </tr>');
        feather.replace();
    }
    removeOptions(dropdown);
    for (var j = 0; j < allJsonData.data.length; j++) {
        timeline = allJsonData.data[j];
        var option = document.createElement('option');
        option.text = timeline.name;
        option.value = timeline.pk;
        dropdown.add(option, dropdown.length);
    }
}

function removeOptions(selectbox) {
    var i;
    for (i = selectbox.options.length - 1; i >= 1; i--) {
        selectbox.remove(i);
    }
}
