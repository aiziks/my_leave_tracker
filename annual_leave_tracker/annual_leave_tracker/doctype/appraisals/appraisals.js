// Copyright (c) 2021, Swifta Systems and contributors
// For license information, please see license.txt

frappe.ui.form.on('Appraisals', {

	end_date: function(frm){
		if(frm.doc.start_date >= frm.doc.end_date){
			console.log(frm.doc.start_date);
			console.log(frm.doc.end_date);
			 frm.set_value('start_date','');
			 frm.set_value('end_date','');
			 frappe.throw('End date must be greater than start date');
			}
		},

	before_save: function(frm){
		if (frm.is_new()){
            frm.set_value('status', "Pending");
            frm.set_value('stage', "Pending Appraiser Review");
        }else if(frm.doc.stage == 'Pending Appraiser Review'){
            frm.set_value('status', "In progress");
            frm.set_value('stage', "Appraiser Review Completed");
			update_overal_score_and_over_score_in_percentage(frm);
			setRatingDisplay(frm, flt(frm.doc.overal_score_in_percentage));
			console.log('now displaying overall score and grade');
        }else if(frm.doc.stage == 'Appraiser Review Completed'){
            if(frm.doc.appraisal_select == 'I disagree with the appraisal'){
                frm.set_value('status', "Rejected");
                frm.set_value('stage', "Appraisee Rejected Review");
            }else{
                frm.set_value('status', "Approved");
             	frm.set_value('stage', "Appraisee Approved Review");
            }
        }

	},

	after_save: function(frm){
		console.log('script after save called');
	},

	status: function(frm){
		console.log('status code triggered: '+ frm.doc.status);
	},

	validate: function (frm){

        console.log("validate,triggered: ");

        var error_exist = 0;


        if(error_exist == 0){
        	$.each(frm.doc.form_goal || [], function(i, row){
        		console.log('row called for validation: '+ row.idx)
        		if(user_on_session(frm) == 'appraisee'){
        			if(!row.appraisees_rating){
        				error_exist = 1;
        				show_error_dialog('Character Appraisee\'s Rating')
        			}else{
        				return;
        			}

        		}else if(user_on_session(frm) == 'appraiser'){
        			if(!row.appraisers_rating){
        				error_exist = 1;
	        			show_error_dialog('Character Appraiser\'s Rating')
	        		}else{
	        			return;
	        		}
        		}
        	})
        }


        if(error_exist == 0){
        	$.each(frm.doc.tab_competence || [], function(i, row){
        		console.log('row called for validation: '+ row.idx)
        		if(user_on_session(frm) == 'appraisee'){
	        		if(!row.appraisees_rating){
	        			error_exist = 1;
	        			show_error_dialog('Competence Appraisee\'s Rating')
	        		}else{
	        			return;
	        		}
	        	}else if(user_on_session(frm) == 'appraiser'){
	        		if(!row.appraisers_rating){
	        			error_exist = 1;
	        			show_error_dialog('Competence Appraiser\'s Rating')
	        		}else{
	        			return;
	        		}
	        	}
        	})
        }



	    if(error_exist == 0){
	    	$.each(frm.doc.tab_capacity || [], function(i, row){
	        	console.log('row called for validation: '+ row.idx)
	        	if(user_on_session(frm) == 'appraisee'){
	        		if(!row.appraisees_rating){
	        			error_exist = 1;
	        			show_error_dialog('Capacity Appraisee\'s Rating')
	        		}else{
	        			return;
	        		}
	        	}else if(user_on_session(frm) == 'appraiser'){
	        		if(!row.appraisers_rating){
	        			error_exist = 1;
	        			show_error_dialog('Capacity Appraiser\'s Rating')
	        		}else{
	        			return;
	        		}
		        }
	        })
	    }

		if(error_exist == 0){
	    	$.each(frm.doc.form_goal1 || [], function(i, row){
	        	console.log('row called for validation: '+ row.idx)
	        	if(user_on_session(frm) == 'appraisee'){
	        		if(!row.appraisees_rating){
	        			error_exist = 1;
	        			show_error_dialog('Goal Appraisee\'s Rating')
	        		}else{
	        			return;
	        		}
	        	}else if(user_on_session(frm) == 'appraiser'){
	        		if(!row.appraisers_rating){
	        			error_exist = 1;
	        			show_error_dialog('Goal Appraiser\'s Rating')
	        		}else{
	        			return;
	        		}
		        }
	        })
	    }

	    if(frm.doc.stage == 'Appraiser Review Completed'){
	    	console.log('frm.doc.appraisee_comment: '+ frm.doc.appraisee_comment);
	    	if(error_exist == 0){
		    	if(!frm.doc.appraisal_select){
		    		error_exist = 1;
		        	show_error_dialog('Review with staff')
		    	}else if(!frm.doc.appraisee_comment){
		    		console.log('appraisee_comment null')
		    		error_exist = 1;
		    		show_error_dialog('Appraisee Comments');
		    	}else{
		    		console.log('appraisee_comment not null');
		    	}
		    }else{
		    	console.log('error_exist not zero');
		    }

		}

		if(frm.doc.stage == 'Appraisee Rejected Review' || frm.doc.stage == 'Appraisee Approved Review'){
	    	if(error_exist == 0){
		    	if(frm.doc.summary_of_strength ==  null){
		    		error_exist = 1;
		        	show_error_dialog('Summary of Strength')
		    	}else if(frm.doc.summary_of_areas_of_improvement == null){
		    		error_exist = 1;
		    		show_error_dialog('Summary of Areas of Improvement');
		    	}else if(frm.doc.training_needs == null){
		    		error_exist = 1;
		    		show_error_dialog('Training Needs');
		    	}else if(frm.doc.appraiser_comment == null){
		    		error_exist = 1;
		    		show_error_dialog('Appraiser\'s Comments');
		    	}
		    }

		}

    },
	onload: function (frm) {

    	console.log('onload function: Appraisals');
		console.log(cur_frm);

    	frm.disable_save();

    	if(frm.doc.start_date && frm.doc.end_date){
    		frm.toggle_enable(['start_date', 'end_date'], false)
    	}
		//

		if(frm.is_new()){
			var df = frappe.meta.get_docfield("Appraisal Goals","appraisees_rating", cur_frm.doc.name);
			df.read_only = 0;
		}else{
			var df = frappe.meta.get_docfield("Appraisal Goals","appraisers_rating", cur_frm.doc.name);
			df.read_only = 0;
		}

      	if (frm.is_new()) {

        	frm.set_value('status', "New");

          	var vdesignation;

          	if(frappe.user.has_role("Employee")){
				console.log("session user: "+frappe.session.user)
				frappe.call({
					method:"erp_generic.erp_generic.doctype.appraisals_template.appraisals_template.get_template_form",
					args:{
						user_id: frappe.session.user
					},
					callback: function(r){
						console.log("response : "+ JSON.stringify(r.message));
						vdesignation = r.message;
						frm.set_value('appraisals_template', vdesignation.template_form)
						frm.set_value('employee_name', vdesignation.employee_full_name)
						frm.set_value('employee', vdesignation.employee_name)
						frm.set_value('employee_number', vdesignation.employee_number)
						frm.set_value('reporting_manager_email', vdesignation.employee_reporting_mn_email)
						frm.set_value('appraisee_category', vdesignation.employee_category)
						//   display_fields(vdesignation.employee_category);
						frm.trigger('refresh_p');
					}

				});

          	}

	    }
    },


    onload_post_render: function (frm){
    	console.log('onload_post_render');
    },

    refresh: function (frm){
		//document.querySelectorAll(".form-comments")[0].style.display="none";
    	console.log('refresh called');

    	$('window').load(function(){
    		console.log('user_on_session(frm) :'+ user_on_session(frm));
    	})


    	frm.disable_save();

    	if (user_on_session(frm) == 'appraiser'){
    		console.log('appraiser function called');
    		toggle_appraisers_rating(frm);
    	}

    	if (user_on_session(frm) == 'appraisee'){
    		console.log('appraisee function called');
    		toggle_appraisees_rating(frm);
    	}

    	// disable_buttons(frm);


    	if(frappe.user.has_role("HR Manager")){
    		frm.enable_save();
        	$.each(frm.doc.table_62 || [], function(i, row){

        		console.log('row.idx: '+ row.name + ' doctype: '+ row.parentfield);

        		frm.fields_dict[row.parentfield].grid.grid_rows_by_docname[row.name].columns.remark_comment.click(

        			function(e) {

        				console.log(e)

        				$("div[data-name=" + "\""+ row.name+"\"" +"]").find("div[data-fieldname="+"\"remark_comment\""+"]").find(".field-area").find("div[data-fieldname="+"\"remark_comment\""+"]").find("input[data-fieldname="+"\"remark_comment\""+"]").prop('disabled', false);

						});


					console.log('called');

		});
        	$("div[data-fieldname="+"\"summary_of_strength\""+"]").closest(".row, .form-section, .empty-section").addClass('visible-section').removeClass('empty-section');
			$(".row, .form-section, .empty-section");


        }else{
        	console.log('Not HR Manager');
        };

    },

	end_date: function(frm){
		console.log("Am here ....")
    	if(frm.doc.start_date >= frm.doc.end_date){
			console.log(frm.doc.start_date);
			console.log(frm.doc.end_date);
			frm.set_value('start_date','');
			frm.set_value('end_date','');
			frappe.throw('End date must be greater than start date');
    	}
	},
	
    appraisals_template: function(frm) {
         frm.doc.form_goal = [];
         frm.doc.tab_competence = [];
         frm.doc.tab_capacity = [];
         frm.doc.table_52 = [];
         frm.doc.table_62 = [];
         erpnext.utils.map_current_doc({
             method: "erp_generic.erp_generic.doctype.appraisals_template.appraisals_template.fetch_appraisal_template",
             source_name: frm.doc.appraisals_template,
             frm: frm

         });

     },

	appraisal_select: function(frm){
	console.log('appraisal_select called');
	dialog_prompt(frm);
	},

});

frappe.ui.form.on('Appraisal Goals', {
    appraisees_rating: function (frm, cdt, cdn) {
    	var sum =0;

    	$.each(frm.doc.form_goal1 || [], function(i, row){
    		console.log('row.appraisees_rating is : '+ row.appraisees_rating + 'index: '+ i + 'idx is: '+ row.idx);
    		if(row.appraisees_rating > 5){
    			frappe.model.set_value(cdt, cdn, "appraisees_rating", 0);
    			frappe.throw('Rating figure not allowed, value should be below or 5');
    		}

    		sum += flt(row.appraisees_rating);

        })

        frm.set_value('appraisees_total_score1', sum);
    },

    appraisers_rating: function (frm, cdt, cdn) {
    	var sum =0;
    	var x=0;
    	var idx = 1
    	$.each(frm.doc.form_goal1 || [], function(i, row){
    		x++;
    		console.log('row.appraisers_rating is : '+ row.appraisers_rating);

    		if(row.appraisers_rating > 5){
    			frappe.model.set_value(cdt, cdn, "appraisers_rating", 0);
    			frappe.throw('Rating figure not allowed, value should be below or 5');
    		}
    		console.log('sum is '+ sum);

    		sum += flt(row.appraisers_rating);

        })

        console.log('sum is: '+ sum);

        // update_overall_summary(frm, idx, sum/(x*5).toFixed(2));

        frm.set_value('appraisers_total_score1', sum);
        frm.set_value('appraisers_total_score_total_wei1', x * 5);
    }
});


frappe.ui.form.on('Appraisals Goal', {
    appraisees_rating: function (frm, cdt, cdn) {
    	var sum =0;

    	$.each(frm.doc.form_goal || [], function(i, row){
    		console.log('row.appraisees_rating is : '+ row.appraisees_rating + 'index: '+ i + 'idx is: '+ row.idx);
    		if(row.appraisees_rating > 5){
    			frappe.model.set_value(cdt, cdn, "appraisees_rating", 0);
    			frappe.throw('Rating figure not allowed, value should be below or 5');
    		}

    		sum += flt(row.appraisees_rating);

        })

        frm.set_value('appraisees_total_score', sum);
    },

    appraisers_rating: function (frm, cdt, cdn) {
    	var sum =0;
    	var x=0;
    	var idx = 1
    	$.each(frm.doc.form_goal || [], function(i, row){
    		x++;
    		console.log('row.appraisers_rating is : '+ row.appraisers_rating);

    		if(row.appraisers_rating > 5){
    			frappe.model.set_value(cdt, cdn, "appraisers_rating", 0);
    			frappe.throw('Rating figure not allowed, value should be below or 5');
    		}
    		console.log('sum is '+ sum);

    		sum += flt(row.appraisers_rating);

        })

        console.log('sum is: '+ sum);

        // update_overall_summary(frm, idx, sum/(x*5).toFixed(2));

        frm.set_value('appraisers_total_score', sum);
        frm.set_value('appraisers_total_score_total_wei', x * 5);
    }
});

frappe.ui.form.on('Appraisals Goal Competence', {
    appraisees_rating: function (frm, cdt, cdn) {
    	var sum =0;
    	$.each(frm.doc.tab_competence || [], function(i, row){
    		console.log('row.appraisees_rating is 2 : '+ parseInt(row.appraisees_rating));
    		if(row.appraisees_rating > 5){
    			frappe.model.set_value(cdt, cdn, "appraisees_rating", 0);
    			frappe.throw('Rating figure not allowed, value should be below or 5');
    		}

    		sum += flt(row.appraisees_rating);

        })
        console.log('sum is: '+ sum);

        frm.set_value('appraisees_total_score_comp', sum);
    },

    appraisers_rating: function (frm, cdt, cdn) {
    	var sum =0;
    	var x=0;
    	var idx = 2
    	$.each(frm.doc.tab_competence || [], function(i, row){
    		x++;
    		console.log('row.appraisers_rating is : '+ row.appraisers_rating);

    		if(row.appraisers_rating > 5){
    			frappe.model.set_value(cdt, cdn, "appraisers_rating", 0);
    			frappe.throw('Rating figure not allowed, value should be below or 5');
    		}
    		console.log('sum is '+ sum);

    		sum += flt(row.appraisers_rating);

        })

        console.log('sum is: '+ sum);

        // update_overall_summary(frm, idx, flt(sum/(x*5)));

        frm.set_value('appraisers_total_score_comp', sum);
        frm.set_value('appraisers_total_score_comp_total_weight', x * 5);


    }
});

frappe.ui.form.on('Appraisals Goal Capacity', {
    appraisees_rating: function (frm, cdt, cdn) {
    	var sum =0;
    	$.each(frm.doc.tab_capacity || [], function(i, row){
    		console.log('row.appraisees_rating is : '+ row.appraisees_rating);
    		if(row.appraisees_rating > 5){
    			frappe.model.set_value(cdt, cdn, "appraisees_rating", 0);
    			frappe.throw('Rating figure not allowed, value should be below or 5');
    		}

    		sum += flt(row.appraisees_rating);

        })
        console.log('sum is: '+ sum);

        frm.set_value('appraisess_total_score_capa', sum);
    },

    appraisers_rating: function (frm, cdt, cdn) {
    	var sum =0;
    	var x=0;
    	var idx = 3
    	$.each(frm.doc.tab_capacity || [], function(i, row){
    		x++;
    		console.log('row.appraisers_rating is : '+ row.appraisers_rating);

    		if(row.appraisers_rating > 5){
    			frappe.model.set_value(cdt, cdn, "appraisers_rating", 0);
    			frappe.throw('Rating figure not allowed, value should be below or 5');
    		}
    		console.log('sum is '+ sum);

    		sum += flt(row.appraisers_rating);

        })

        console.log('sum is: '+ sum);

        frm.set_value('appraisers_total_score_capa', sum);
        frm.set_value('appraisers_total_score_capa_total_weight', x * 5);

    }
});


var update_overal_score_and_over_score_in_percentage = function(frm){

	var numerator = frm.doc.appraisers_total_score1 + frm.doc.appraisers_total_score + frm.doc.appraisers_total_score_comp + frm.doc.appraisers_total_score_capa;

    var denominator = frm.doc.appraisers_total_score_total_wei1 + frm.doc.appraisers_total_score_total_wei + frm.doc.appraisers_total_score_comp_total_weight + frm.doc.appraisers_total_score_capa_total_weight;
	
	console.log('overall sum is: '+ numerator);

	var result = (numerator/denominator) * 100;
	console.log('result is: '+ result);

	frm.set_value('overall_score', numerator);
	// console.log("sum_weight is: "+ sum_weight);
	if(result){
		frm.set_value('overal_score_in_percentage', flt(result, 2));
	}

}

var grid_row_function = function(frm, grid_row){

	if(grid_row.doc.parentfield == 'table_62'){
		console.log('toggling hapenpening: '+ JSON.stringify(grid_row.doc));
		if(grid_row.doc.idx == 6){
			grid_row.toggle_editable("remark_comment", true);
			// frm.refresh_field('table_62');
		}

	}
}



var toggle_appraisees_rating = function(frm){

	var result;
	console.log('toggle_appraisees_rating called');

	frappe.call({
		method:"erp_generic.erp_generic.doctype.appraisals_template.appraisals_template.fetch_email_id",
		args:{
			employee_name: frm.doc.employee,
			for_reporting_manager: 'False'
		},
		callback: function(r){
			console.log("response_employee_email : "+ JSON.stringify(r.message));
			var result = r.message;

			process_request(result);
		}
	});

	console.log('tablee: '+frm.doc.table_18);

	function process_request(result){

		if(frm.doc.stage == 'Appraiser Review Completed' || frm.doc.status == 'New'){
			console.log('enable_save for appraisee');
			frm.enable_save();
			// frm.reload_doc();
		}else{
			console.log('testingggg')
		}

		
		console.log('form_goal: '+frm.doc.form_goal);

		$.each(frm.doc.form_goal || [], function(i, row){
			var doc_user_id;

			// console.log('status is: '+ frm.doc.status +' and result is: '+ result + ' frappe.session is: '+ frappe.session.user);

			console.log('row name: '+ row.name);

			if(frm.doc.status == 'New' && frappe.session.user == result){

				console.log("Element is: "+ $(".form-group").find("div[data-name=" + "\""+ row.name+"\"" +"]").find("div[data-fieldname="+"appraisees_rating"+"]").find(".field-area").prop('outerHTML'));

				// $(".form-group").find("div[data-name=" + "\""+ row.name+"\"" +"]").find("div[data-fieldname="+"appraisees_rating"+"]").find(".field-area").show();

				$(".form-group").find("div[data-name=" + "\""+ row.name+"\"" +"]").find("div[data-fieldname="+"appraisees_rating"+"]").click(
					function(e){
						console.log('clicked - called');
						$(".form-group").find("div[data-name=" + "\""+ row.name+"\"" +"]").find("div[data-fieldname="+"appraisees_rating"+"]").find(".field-area")
						.find("select[data-fieldname="+"\"appraisees_rating\""+"]").prop('disabled', false);
				});

			}else{
				frm.set_df_property('form_goal', 'read_only', 1);

			}

		});

		$.each(frm.doc.tab_competence || [], function(i, row){

			if(frm.doc.status == 'New' && frappe.session.user == result){

				console.log("Element is: "+ $(".form-group").find("div[data-name=" + "\""+ row.name+"\"" +"]").find("div[data-fieldname="+"appraisees_rating"+"]").find(".field-area").prop('outerHTML'));

				// $(".form-group").find("div[data-name=" + "\""+ row.name+"\"" +"]").find("div[data-fieldname="+"appraisees_rating"+"]").find(".field-area").show();

				$(".form-group").find("div[data-name=" + "\""+ row.name+"\"" +"]").find("div[data-fieldname="+"appraisees_rating"+"]").click(
					function(e){
						console.log('clicked - called');
						$(".form-group").find("div[data-name=" + "\""+ row.name+"\"" +"]").find("div[data-fieldname="+"appraisees_rating"+"]").find(".field-area")
						.find("select[data-fieldname="+"\"appraisees_rating\""+"]").prop('disabled', false);
				});

			}else{
				frm.set_df_property('tab_competence', 'read_only', 1);
			}

		});

		$.each(frm.doc.tab_capacity || [], function(i, row){


			if(frm.doc.status == 'New' && frappe.session.user == result){

				console.log("Element is: "+ $(".form-group").find("div[data-name=" + "\""+ row.name+"\"" +"]").find("div[data-fieldname="+"appraisees_rating"+"]").find(".field-area").prop('outerHTML'));

				// $(".form-group").find("div[data-name=" + "\""+ row.name+"\"" +"]").find("div[data-fieldname="+"appraisees_rating"+"]").find(".field-area").show();

				$(".form-group").find("div[data-name=" + "\""+ row.name+"\"" +"]").find("div[data-fieldname="+"appraisees_rating"+"]").click(
					function(e){
						console.log('clicked - called');
						$(".form-group").find("div[data-name=" + "\""+ row.name+"\"" +"]").find("div[data-fieldname="+"appraisees_rating"+"]").find(".field-area")
						.find("select[data-fieldname="+"\"appraisees_rating\""+"]").prop('disabled', false);
				});

			}else{
				frm.set_df_property('tab_capacity', 'read_only', 1);
			}

		});


		if(frm.doc.status == 'New' && frappe.session.user == result){

			frm.toggle_enable(['appraisee_comment'], true);

			$("div[data-fieldname="+"\"appraisee_comment\""+"]").closest(".row, .form-section, .empty-section").addClass('visible-section').removeClass('empty-section');

		}else if(!frm.doc.appraisee_comment){
			frm.toggle_enable(['appraisee_comment'], true);

			$("div[data-fieldname="+"\"appraisee_comment\""+"]").closest(".row, .form-section, .empty-section").addClass('visible-section').removeClass('empty-section');
		}
		// frm.toggle_display(['appraisee_comment'], true);

		if(frm.doc.stage == 'Appraiser Review Completed' && frappe.session.user == result){
			console.log('unhide appraisal_select');

			frm.toggle_display(['appraisal_select'], true);

			if(!frm.doc.appraisal_select){
				frm.toggle_enable(['appraisal_select'], true);
			}

			$("div[data-fieldname="+"\"appraisal_select\""+"]").closest(".row, .form-section, .empty-section").addClass('visible-section').removeClass('empty-section');

		}else{
			frm.toggle_display(['appraisal_select'], true);

			$("div[data-fieldname="+"\"appraisal_select\""+"]").closest(".row, .form-section, .empty-section").addClass('visible-section').removeClass('empty-section');
		}

		console.log('end of function');

	}
}

var toggle_appraisers_rating = function(frm){

	var result;

	frappe.call({
		method:"erp_generic.erp_generic.doctype.appraisals_template.appraisals_template.fetch_email_id",
		args:{
			employee_name: frm.doc.employee,
			for_reporting_manager: 'True'
		},
		callback: function(r){
			console.log("response_appraiseer_email : "+ JSON.stringify(r.message));
			result = r.message;

			process_request(result);
		}
	});

	function process_request(result){
		if(frm.doc.stage == 'Pending Appraiser Review' || frm.doc.stage == 'Appraisee Approved Review' || frm.doc.stage == 'Appraisee Rejected Review'){
			console.log('enable_save for appraiser');
			frm.enable_save();
		}else{
			console.log('appraiser disable buttion');
		}
		
		$.each(frm.doc.form_goal || [], function(i, row){


			if(frm.doc.stage == 'Pending Appraiser Review' && frappe.session.user == result){

				$(".form-group").find("div[data-name=" + "\""+ row.name+"\"" +"]").find("div[data-fieldname="+"appraisers_rating"+"]").click(
					function(e){
						console.log('clicked - called');
						$(".form-group").find("div[data-name=" + "\""+ row.name+"\"" +"]").find("div[data-fieldname="+"appraisers_rating"+"]").find(".field-area")
						.find("select[data-fieldname="+"\"appraisers_rating\""+"]").prop('disabled', false);
				});

			}else{
				frm.set_df_property('form_goal', 'read_only', 1);
			}

		});

		$.each(frm.doc.tab_competence || [], function(i, row){


			if(frm.doc.stage == 'Pending Appraiser Review' && frappe.session.user == result){

				console.log('tab_competence: '+ row.name + ' result: '+ result);

				$(".form-group").find("div[data-name=" + "\""+ row.name+"\"" +"]").find("div[data-fieldname="+"appraisers_rating"+"]").click(
					function(e){
						console.log('clicked - called');
						$(".form-group").find("div[data-name=" + "\""+ row.name+"\"" +"]").find("div[data-fieldname="+"appraisers_rating"+"]").find(".field-area")
						.find("select[data-fieldname="+"\"appraisers_rating\""+"]").prop('disabled', false);
				});

			}else{
				frm.set_df_property('tab_competence', 'read_only', 1);
			}

		});

		$.each(frm.doc.tab_capacity || [], function(i, row){

			if(frm.doc.stage == 'Pending Appraiser Review' && frappe.session.user == result){
				console.log('tab_capacity: '+ row.name + ' result: '+ result);

				$(".form-group").find("div[data-name=" + "\""+ row.name+"\"" +"]").find("div[data-fieldname="+"appraisers_rating"+"]").click(
					function(e){
						console.log('clicked - called');
						$(".form-group").find("div[data-name=" + "\""+ row.name+"\"" +"]").find("div[data-fieldname="+"appraisers_rating"+"]").find(".field-area")
						.find("select[data-fieldname="+"\"appraisers_rating\""+"]").prop('disabled', false);
				});
			}else{
				frm.set_df_property('tab_capacity', 'read_only', 1);
			}

		});

		$.each(frm.doc.table_62 || [], function(i, row){


			if(frm.doc.stage == 'Pending Appraiser Review' && frappe.session.user == result){


					console.log('row.idx: '+ row.name + ' doctype: '+ row.parentfield);

					frm.fields_dict[row.parentfield].grid.grid_rows_by_docname[row.name].columns.remark_comment.click(
						function(e) {
							console.log(e)

							$("div[data-name=" + "\""+ row.name+"\"" +"]").find("div[data-fieldname="+"\"remark_comment\""+"]").find(".field-area").find("div[data-fieldname="+"\"remark_comment\""+"]").find("input[data-fieldname="+"\"remark_comment\""+"]").prop('disabled', false);

						});


					console.log('called');

			}else if(frm.doc.stage == 'Appraisee Approved Review' || frm.doc.stage == 'Appraisee Rejected Review'){

				console.log('row.idx: '+ row.name + ' doctype: '+ row.parentfield);

					frm.fields_dict[row.parentfield].grid.grid_rows_by_docname[row.name].columns.remark_comment.click(
						function(e) {
							console.log(e)

							$("div[data-name=" + "\""+ row.name+"\"" +"]").find("div[data-fieldname="+"\"remark_comment\""+"]").find(".field-area").find("div[data-fieldname="+"\"remark_comment\""+"]").find("input[data-fieldname="+"\"remark_comment\""+"]").prop('disabled', false);

						});

			}else{
				frm.set_df_property('table_62', 'read_only', 1);
			}

		});

		if(frm.doc.stage == 'Pending Appraiser Review' && frappe.session.user == result){
			console.log('enable summary_of_areas_of_improvement and rest');

			$("div[data-fieldname="+"\"summary_of_strength\""+"]").closest(".row, .form-section, .empty-section").addClass('visible-section').removeClass('empty-section');
			$(".row, .form-section, .empty-section");

			if(!frm.doc.summary_of_strength){
				frm.toggle_enable(['summary_of_strength'], true);
			}
			if(!frm.doc.summary_of_areas_of_improvement){
				frm.toggle_enable(['summary_of_areas_of_improvement'], true);
			}
			if(!frm.doc.training_needs){
				frm.toggle_enable(['training_needs'], true);
			}
			if(!frm.doc.appraiser_comment){
				frm.toggle_enable(['appraiser_comment'], true);
			}

			// frm.toggle_enable(['summary_of_strength', 'summary_of_areas_of_improvement', 'training_needs','appraiser_comment'], true);

			console.log('toggle_enable');
		}else if(frm.doc.stage == 'Appraisee Approved Review' || frm.doc.stage == 'Appraisee Rejected Review' ){
			console.log('enable summary_of_areas_of_improvement and rest');

			$("div[data-fieldname="+"\"summary_of_strength\""+"]").closest(".row, .form-section, .empty-section").addClass('visible-section').removeClass('empty-section');
			$(".row, .form-section, .empty-section");

			if(!frm.doc.summary_of_strength){
				frm.toggle_enable(['summary_of_strength'], true);
			}
			if(!frm.doc.summary_of_areas_of_improvement){
				frm.toggle_enable(['summary_of_areas_of_improvement'], true);
			}
			if(!frm.doc.training_needs){
				frm.toggle_enable(['training_needs'], true);
			}
			if(!frm.doc.appraiser_comment){
				frm.toggle_enable(['appraiser_comment'], true);
			}
		}

	}

}

var send_email = function(doc, to, doc_name){

	console.log('send_email called');
	frappe.call({
		method:"erp_generic.erp_generic.doctype.appraisals_template.appraisals_template.send_email",
		args:{
			emp_id: doc.employee,
			to: to,
			doc_name: doc_name
		},
		callback: function(r){
			frappe.msgprint({
				title: __('Notification'),
				indicator: 'green',
				message: __('Employee has been notified, thanks.')
			});
		}
	});
}

var dialog_prompt = function(frm){
	if(frm.doc.appraisal_select){
		frappe.confirm('<p> Are you sure of your selection below: </p><p>' + frm.doc.appraisal_select + '? </p>',
		() => {
			frm.save()
			show_alert('Thanks & Have a Nice Day')
		})
	}
}

var disable_buttons = function(frm){
	console.log('hide buttons');

}


var user_on_session = function(frm){
	console.log('frm.doc.reporting_manager_email:' + frm.doc.reporting_manager_email);
	console.log(frm.doc)
	if(frm.doc.reporting_manager_email){
		if(frm.doc.reporting_manager_email == frappe.session.user){
			console.log("user_on_session: appraiser");
			return "appraiser";
		}else{
			console.log("user_on_session: appraisee");
			return "appraisee";
		}
	}else{
		console.log('reporting_manager_email is null');

	}
}


var setRatingDisplay = (frm, score)=>{
	console.log("DISPLAY RATING")
	console.log(score)
	if(score){
		if(score >= 96 && score <= 100)
			frm.set_value('grade', "A+ Exceptional");
		else if(score >= 86 && score <= 95)
			frm.set_value('grade', "A- Outstanding");
		else if(score >= 75 && score <= 85)
			frm.set_value('grade', "B Good");
		else if(score >= 65 && score <= 74)
			frm.set_value('grade', "C Above Average");
		else if(score >= 50 && score <= 64)
			frm.set_value('grade', "D Average");
		else if(score < 50)
			frm.set_value('grade', "E Unsatisfactory");
		else
			frm.set_value('grade', " ");
	}
}


var show_error_dialog = function(value){
	        	console.log(value +' is empty')
	        	var name = 'Character'
	        	frappe.validated = false;
	        	frappe.throw({
				    title: __('Error'),
				    indicator: 'red',
				    message: __('Please fill the '+value+' before saving')
			});

        }

var show_error_dialogv2 = function(score, benchmark){
			// console.log(value +' is empty')
			var name = 'Character'
			frappe.validated = false;
			frappe.throw({
				title: __('Total Score – Score Card'),
				indicator: 'red',
				message: __('Score must NOT be greater than '+benchmark+'!')
		});

	}

function set_valiation(){
	console.log('set validation called');
	frappe.validated = true;
}
