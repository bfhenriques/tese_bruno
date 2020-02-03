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

function addContent() {
    var selected = document.getElementById("timeline_dropdown");

    contents_json = all_contents.replace(/&quot;/ig, '"');
    var jsonData = JSON.parse(contents_json);

    table = table_contents.replace(/&quot;/ig, '"');
    var tableJsonData = JSON.parse(table);

    for (var i = 0; i < jsonData.data.length; i++) {
        var content = jsonData.data[i];
        if (content.pk.toString() === selected.options[selected.selectedIndex].value) {
            var duration_col = '';
            if (content.file_type === "image" || content.file_type === "pdf" || content.file_type === "ppt") {
                duration_col = '<td><input class="form-control" type="number" name="durations" min="1" max="100" value="' + content.duration + '" required/></td>\n';
            }
            else {
                duration = -1;
                for (var x = 0; x < tableJsonData.data.length; x++) {
                    if (tableJsonData.data[x].pk === content.pk){
                        duration = tableJsonData.data[x].duration;
                        break;
                    }
                }
                if (duration === -1){
                    duration = content.duration;
                }
                duration_col = '<td><input class="form-control" type="hidden" name="durations" value="' + duration + '" required/>' + duration + '</td>\n';
            }
            $(add_table).find('tbody').append('' +
                '<tr>\n' +
                '                        <td><input type="hidden" class="form-control" name="pks" value="' + content.pk + '" /></td>' +
                '                        <td>' + content.name + '</td>\n' +
                '                        <td>' + content.creator + '</td>\n' +
                '                        <td>' + content.creation_date + '</td>\n' +
                '                        <td>' + content.last_modified + '</td>\n' +
                duration_col +
                '                        <td><a class="btn btn-default btn-sm" onclick="deleteContentRow(this)">\n' +
                '                          <span class="glyphicon glyphicon-plus" aria-hidden="true"></span><svg data-feather="trash-2"></svg>\n' +
                '                        </a></td>\n' +
                '                    </tr>');
            feather.replace();
            break;
        }
    }

}

function deleteContentRow(btn) {
    var row = btn.parentNode.parentNode;
    row.parentNode.removeChild(row);
}

function populate() {
    var dropdown = document.getElementById("timeline_dropdown");

    table = table_contents.replace(/&quot;/ig, '"');
    var tableJsonData = JSON.parse(table);

    all = all_contents.replace(/&quot;/ig, '"');
    var allJsonData = JSON.parse(all);

    $("#add_table tbody tr").remove();
    for (var i = 0; i < tableJsonData.data.length; i++) {
        var content = tableJsonData.data[i];
        var duration_col = '';
        if (content.file_type === "image" || content.file_type === "pdf" || content.file_type === "ppt") {
            duration_col = '<td><input class="form-control" type="number" min="1" max="100"  name="durations" value="' + content.duration + '" required/></td>\n';
        }
        else {
            duration_col = '<td><input class="form-control" type="hidden" name="durations" value="' + content.duration + '" required/>' + content.duration + '</td>\n';
        }
        $(add_table).find('tbody').append('' +
            '<tr>\n' +
            '                        <td><input type="hidden" class="form-control" name="pks" value="' + content.pk + '" /></td>' +
            '                        <td>' + content.name + '</td>\n' +
            '                        <td>' + content.creator + '</td>\n' +
            '                        <td>' + content.creation_date + '</td>\n' +
            '                        <td>' + content.last_modified + '</td>\n' +
            duration_col +
            '                        <td><a class="btn btn-default btn-sm" onclick="deleteContentRow(this)">\n' +
            '                          <span class="glyphicon glyphicon-plus" aria-hidden="true"></span><svg data-feather="trash-2"></svg>\n' +
            '                        </a></td>\n' +
            '                    </tr>');
        feather.replace();
    }
    removeOptions(dropdown);
    for (var j = 0; j < allJsonData.data.length; j++) {
        content = allJsonData.data[j];
        var option = document.createElement('option');
        option.text = content.name;
        option.value = content.pk;
        dropdown.add(option, dropdown.length);
    }
}

function removeOptions(selectbox) {
    var i;
    for (i = selectbox.options.length - 1; i >= 1; i--) {
        selectbox.remove(i);
    }
}
