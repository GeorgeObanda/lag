import pandas as pd
import numpy as np
import os
from cryptography.fernet import Fernet
import pickle
from dateutil.relativedelta import relativedelta
from datetime import date, datetime
from redcap import Project

class ArlModel:
    def decrypt_key(self, k1, k2):
        fd = "C:/Users/george.obanda/OneDrive - Aga Khan University/AKU/ARL/yek/"
        key = open(f"{fd}{k1}.key", "rb").read()
        cipher_suite = Fernet(key)
        with open("{0}{1}.txt".format(fd, k2), "rb") as f:
            encrypted_key = f.read()
        decrypted_key = cipher_suite.decrypt(encrypted_key).decode()
        return decrypted_key

    def backup_encrypt_df(self, df, file="", key_inn=""):
        if not file:
            file = f"C:/Users/george.obanda/OneDrive - Aga Khan University/AKU/ARL/Data/ARL_LBW_Data_Backups/ARL_LBW_data_{datetime.now().strftime('%B-%d-%Y')}"
        try:
            with open("C:/Users/george.obanda/OneDrive - Aga Khan University/AKU/ARL/yek/kepart2.key", "rb") as key_file:
                key_inn = key_file.read()
            cipher = Fernet(key_inn)
            df_serialized = pickle.dumps(df)
            encrypt_df = cipher.encrypt(df_serialized)

            with open(f"{file}", 'wb') as fname:
                fname.write(encrypt_df)
            fname.close()
        except Exception as e:
            print(e)

    def compDfs(self, d_1, d_2, ID):
        print(d_1.shape, d_2.shape)
        d1 = d_1.copy()
        d2 = d_2.copy()
        coln_a = [c for c in d1.columns.to_list() if c not in d2.columns.to_list()]
        coln_b = [c for c in d2.columns.to_list() if c not in d1.columns.to_list()]
        if len(coln_a) > 0:
            print(f"Missing columns in second dataframe: {coln_a}")
            return pd.DataFrame([]), pd.DataFrame([])
        elif len(coln_b) > 0:
            print(f"Missing columns in first dataframe: {coln_b}")
            return pd.DataFrame([]), pd.DataFrame([])
        else:
            try:
                or_cols = [oc for oc in d1.columns if ID not in oc]
                d1.rename(columns=lambda col: f"{col}_ver1" if col not in [ID] else col, inplace=True)
                d2.rename(columns=lambda col: f"{col}_ver2" if col not in [ID] else col, inplace=True)
                df = pd.merge(d1, d2, on=ID, how='outer')
                arg_ls = []
                for cl in or_cols:
                    dls = [c for c in df.columns if c.split('_ver')[0] == cl]
                    arg_ls.append(dls[0])
                    arg_ls.append(dls[1])
                    df[dls[0]] = df[dls[0]].fillna('')
                    df[dls[1]] = df[dls[1]].fillna('')
                    # (df[dls[0y]].notnull())&(df[dls[1]].notnull())&
                    df.loc[(df[dls[0]] != df[dls[1]]), f"{cl}_dff"] = "mismatch"
                    arg_ls.append(f"{cl}_dff")
                return df[[ID] + arg_ls], df.loc[
                    (df[[c for c in df.columns if any(x in c for x in ['_dff'])]] == "mismatch").any(axis=1)]
            except Exception as e:
                print(f"Error returning: {e}")
                return pd.DataFrame([]), pd.DataFrame([])

    def import_decrypt_df(self, file=""):
        if not file:
            print("No file specified")
            return pd.DataFrame()
        else:
            key_inn = input()
            try:
                cipher = Fernet(key_inn)
                with open(file, 'rb') as fname:
                    encrypted_df = fname.read()
                fname.close()
                decrypted_df = cipher.decrypt(encrypted_df)
                deserialized_df = pickle.loads(decrypted_df)
                return deserialized_df
            except Exception as e:
                print(e)
                return pd.DataFrame()

    def rename_Q(self, Q):
        for col in Q.columns:
            if "Query" in col:
                Q.rename(columns={f"{col}": "Query"}, inplace=True)
        return Q

    def trim_data1(self, df):
        for cols in df.columns:
            df[cols] = df[cols].replace(["['']", [""]], np.nan).infer_objects()
        return df

    def trim_data(self, df):
        for col in df.columns:
            df.loc[(df[col].eq("['']")), col] = np.nan
            # df[col] = df[col].fillna('')
        df_obj = df.select_dtypes(include=['object']).fillna('')
        df[df_obj.columns] = df_obj
        return df

    def mergB(self, ds):
        dt = ds.copy()
        dt = pd.merge(dt, bs[['infant_id', 'bs_facility']], on='infant_id', how='left')
        return dt

    import os
    import pandas as pd
    from redcap import Project

    def get_data(self):
        """Gathers data from REDCap server"""

        try:
            print("Starting REDCap connection...")

            # ==========================================
            # REDCap credentials from Railway Variables
            # ==========================================
            url = os.getenv("REDCAP_API_URL")
            token = os.getenv("REDCAP_API_TOKEN")

            if not url:
                raise ValueError("REDCAP_API_URL is missing")

            if not token:
                raise ValueError("REDCAP_API_TOKEN is missing")

            print("Connecting to REDCap...")

            # ==========================================
            # Connect to REDCap
            # ==========================================
            arl = Project(url, token)

            print("Downloading records...")

            # ==========================================
            # Export records
            # ==========================================
            data = arl.export_records(
                format_type='df',
                df_kwargs={'index_col': 'infant_id'}
            )

            print(f"Downloaded data shape: {data.shape}")

            # ==========================================
            # Reset index
            # ==========================================
            data = data.reset_index()

            # ==========================================
            # Process MID columns
            # ==========================================
            for col in [c for c in data.columns if '_mid' in c]:

                if 'infant_id' in data.columns:
                    data[col] = (
                        data['infant_id']
                        .astype(str)
                        .str.split('-')
                        .str[0]
                    )

            print("Gathered data successfully")

            return data

        except Exception as e:

            import traceback

            print("FULL ERROR:")
            print(traceback.format_exc())

            return pd.DataFrame()

    def const_arl(self, dat):
        """Cosnstructs list values for checkboxes from the Master databases and drops subset
           columnn values (replicated with ___) maintaining primary column name
        """
        df = dat.copy()
        try:
            for col_n in set(col.split('___')[0] for col in df.columns if "___" in col):
                columns_to_check = [col for col in df.columns.to_list() if col.startswith(col_n) and "___" in col]
                df[columns_to_check] = df[columns_to_check].astype(str)
                for col in columns_to_check:
                    choice_i = df[col].name.split("___")[1]
                    df.loc[(df[col] == "1") | (df[col] == 1) | (df[col] == "1.0") | (df[col] == 1.0), col] = choice_i
                    df[col_n] = df[columns_to_check].astype(str).apply(lambda x: ','.join([value for value in x if (
                                (value != '0') & (value != 0) & (value != 0.0) & (value != "0.0") & (value != "nan") & (
                                    value.strip() != ''))]), axis=1).str.split(',').apply(list)
                    df[col_n] = df[col_n].astype(str)
                    # df[col_n] = df[col_n].fillna('')
                df.drop(columns_to_check, axis=1, inplace=True)
            mids = [x for x in df.columns if "_mid" in x]
            dcolls = [y for y in df.columns if "_interviewer" in y]
            for col in mids:
                df[col] = df['infant_id'].str[:8]
            for col in dcolls:
                df[col] = df[col].map({1: 'LAM', 2: 'MB', 3: 'MMK', 4: 'SRK'})
            return df
        except Exception as e:
            print("Error returning: {}".format(e))
            return pd.DataFrame([])

    def refine(self, dat):
        """Refines data to provide calculated values"""
        ds = dat.copy()
        ds['mbf_score2'] = ds['mbf_inner_satisfaction'] + ds['mbf_special_moments'] + ds['mbf_interest_breastfeed'] + \
                           ds['mbf_loved_breastfeed'] + ds['mbf_burden_source'] + ds['mbf_connected'] + ds[
                               'mbf_suckled'] + ds['mbf_exhausting'] + ds['mbf_important_breastfeed'] + ds[
                               'mbf_growth'] + ds['mbf_worked'] + ds['mbf_nurturing'] + ds['mbf_conscious'] + ds[
                               'mbf_tied'] + ds['mbf_worried'] + ds['mbf_calmed'] + ds['mbf_fulfilling'] + ds[
                               'mbf_produce'] + ds['mbf_trouble'] + ds['mbf_feel_like'] + ds['mbf_enjoyed'] + ds[
                               'mbf_anxious'] + ds['mbf_confident'] + ds['mbf_gained_weight'] + ds['mbf_secure'] + ds[
                               'mbf_fit_activities'] + ds['mbf_relax'] + ds['mbf_emotional'] + ds['mbf_wonderful']
        ds['mw_score2'] = ds['mw_hurt'] + ds['mw_interest'] + ds['mw_down'] + ds['mw_sleep'] + ds['mw_tired'] + ds[
            'mw_appetite'] + ds['mw_bad'] + ds['mw_conc'] + ds['mw_move']
        return ds

    def reconst(self, dat):
        """Restructures the Master database into individual arms for each event
           Args:
               df (Dataframe): The master database
           Return: List of event databases
        """
        data = dat.copy()
        try:
            df = self.const_arl(data)
            baseline = df.loc[(df['redcap_event_name'] == "baseline_arm_1")][
                ['infant_id', 'redcap_event_name', 'bs_facility', 'bs_facility_rf', 'bs_mid', 'unit_code_number',
                 'bs_interviewer', 'enrollment_date', 'infant_initals', 'infant_dob', 'child_sex',
                 'infant_single_twin_tri', 'first_enl', 'twin_enl', 'twin_enl_id', 'twin_enl_reason', 'twin_enl_2',
                 'twin_enl_id_2', 'twin_enl_reason_2', 'twin_enl_3', 'twin_enl_id_3', 'twin_enl_reason_3',
                 'cg_initials', 'cg_dob', 'cg_infant_rship', 'cg_infant_rship_other', 'infant_mother_alive',
                 'infant_father_alive', 'cg_contact', 'cg_contact_dk', 'cg_contact_alt', 'cg_contact_alt_dk',
                 'cg_residence', 'mt_adm_date', 'mt_dsc_date', 'bth_weight_11', 'bth_weight_12', 'bth_weight_21',
                 'bth_weight_22', 'bth_weight_31', 'bth_weight_32', 'bth_weight_final', 'bth_weight_dk',
                 'bth_length_11', 'bth_length_12', 'bth_length_21', 'bth_length_22', 'bth_length_31', 'bth_length_32',
                 'bth_length_final', 'bth_length_dk', 'bth_head_circum_11', 'bth_head_circum_12', 'bth_head_circum_21',
                 'bth_head_circum_22', 'bth_head_circum_31', 'bth_head_circum_32', 'bth_head_circum_final',
                 'bth_head_circum_dk', 'dsc_weight_11', 'dsc_weight_12', 'dsc_weight_21', 'dsc_weight_22',
                 'dsc_weight_31', 'dsc_weight_32', 'dsc_weight_final', 'dsc_length_11', 'dsc_length_12',
                 'dsc_length_21', 'dsc_length_22', 'dsc_length_31', 'dsc_length_32', 'dsc_length_final',
                 'dsc_head_circum_11', 'dsc_head_circum_12', 'dsc_head_circum_21', 'dsc_head_circum_22',
                 'dsc_head_circum_31', 'dsc_head_circum_32', 'dsc_head_circum_final', 'dsc_muac_11', 'dsc_muac_12',
                 'dsc_muac_21', 'dsc_muac_22', 'dsc_muac_31', 'dsc_muac_32', 'dsc_muac_final',
                 'ethnicity', 'ethnicity_other', 'religion', 'religion_other', 'marital_status', 'education_level',
                 'income_source', 'income_source_other', 'household_number', 'children_less15yrs', 'people_15_64',
                 'people_over_65yrs', 'children_care', 'children_care_other', 'hh_head', 'hh_head_other',
                 'hh_head_infant_rship', 'hh_head_educ_level', 'hh_head_income_source', 'first_pregnancy',
                 'pregnant_times', 'children_alive', 'miscarriages', 'miscarriages_number', 'had_preterm', 'preterm_no',
                 'neodeath_first', 'neodeath_first_no', 'neodeath_after', 'neodeath_after_no', 'breastfeeding_start',
                 'difficulty_feeding', 'difficulty_feeding_summary', 'feed_not_be4_breastmilk', 'fluids_feeds_list',
                 'baby_feeds', 'baby_feeds_other', 'feeding_method', 'feeding_method_other', 'times_breastfed_24hrs',
                 'kangaroo_mc_training', 'kangaroo_mc_practice', 'kangaroo_mc_challenges', 'kangaroo_mc_challenge_oth',
                 'baby_warmth_source', 'baby_warmth_source_other', 'vitamin_k_after_birth', 'bcg_polio', 'cord_method',
                 'cord_method_other', 'proper_cord_care_info', 'cord_cleaning_conf', 'antenal_visits_no',
                 'distance_to_health_fac', 'mode_of_transport', 'mode_of_transport_other', 'distance_nearest_fac',
                 'anc_payment', 'amount_paid', 'anc_affordable', 'anc_payment_public_hc', 'cwc_service_payment',
                 'cwc_public_hc', 'medical_care', 'medical_care_other', 'baby_warm_knowledge', 'baby_warmth_hm',
                 'baby_warmth_hm_other', 'baby_clean_knowledge', 'baby_cleaning_advice_hm',
                 'baby_cleaning_advice_other', 'breastfeeding_knowledge', 'feeding_baby_hm', 'feeding_baby_hm_other',
                 'hiv_pos_transmission',
                 'hiv_trans_info', 'hiv_trans_info_other', 'baby_immunization_info', 'breathing_problems_help',
                 'dificulty_brestfeding_help', 'fever_help', 'cold_touch_help', 'convulsions_help', 'jaundice_help',
                 'eye_help', 'umbilical_cord_help', 'delivery_location', 'delivery_location_other',
                 'labour_complications', 'labour_complications_list', 'labour_complications_other', 'ga_at_birth',
                 'ga_by', 'ga_by_other', 'apgar_score_1_min', 'apgar_score_5_min', 'apgar_score_10_min',
                 'breathing_support', 'mt_complications', 'mt_complications_other', 'baby_admission_unit',
                 'hc_facility_admitted', 'days_baby_admitted', 'admission_reason', 'admission_reason_other',
                 'baby_diagnosis', 'baby_diagnosis_other', 'cord_clean', 'unit_admission_date', 'unit_discharge_date',
                 'bs_comment', 'wi_mid', 'wi_first', 'wi_interviewer', 'wi_house', 'wi_pump', 'wi_radio', 'wi_tv',
                 'wi_watch', 'wi_mobile', 'wi_fridge', 'wi_table', 'wi_chair', 'wi_sofa', 'wi_sponge_mat',
                 'wi_straw_mat', 'wi_elec_stove', 'wi_kero_lamp', 'we_press_lamp', 'wi_kero_stove', 'wi_gas_stove',
                 'wi_bike', 'wi_motorcycle', 'wi_car', 'wi_solar', 'wi_mill', 'wi_electric', 'wi_sew', 'wi_coffee_land',
                 'wi_comp', 'wi_bank', 'wi_oxen', 'wi_cow', 'wi_calves', 'wi_bull', 'wi_sheep_goat', 'wi_horse',
                 'wi_chicken', 'wi_bee_hive', 'wi_land', 'wi_land_quant', 'wi_land_unit', 'wi_land_unit_other',
                 'wi_income_1', 'wi_income_1_spc', 'wi_income_2', 'wi_income_2_spc', 'wi_cook_loc', 'wi_fuel',
                 'wi_roof', 'wi_wall', 'wi_floor', 'wi_sleep_rooms', 'wi_comments', 'user_nt', 'nt_grains',
                 'nt_grains_times', 'nt_vitamins_vg', 'nt_vitamins_vg_times', 'nt_tubers',
                 'nt_tubers_times', 'nt_leafy', 'nt_leafy_times', 'nt_vegs', 'nt_vegs_times', 'nt_vitamins_ft',
                 'nt_vitamins_ft_times', 'nt_fruits', 'nt_fruits_times', 'nt_organs', 'nt_organs_times', 'nt_meats',
                 'nt_meats_times', 'nt_eggs', 'nt_eggs_times', 'nt_fish', 'nt_fish_times', 'nt_legumes',
                 'nt_legumes_times', 'nt_milk', 'nt_milk_times', 'nt_oils', 'nt_oils_times', 'nt_sweets',
                 'nt_sweets_times', 'nt_sugar', 'nt_sugar_times', 'nt_condiments', 'nt_condiments_times', 'nt_comments',
                 'mbf_mid', 'mbf_interviewer', 'mbf_interview_date', 'mbf_infant_age', 'mbf_assessment_type',
                 'mbf_inner_satisfaction', 'mbf_special_moments', 'mbf_interest_breastfeed', 'mbf_loved_breastfeed',
                 'mbf_burden_source', 'mbf_connected', 'mbf_suckled', 'mbf_exhausting', 'mbf_important_breastfeed',
                 'mbf_growth', 'mbf_worked', 'mbf_nurturing', 'mbf_conscious', 'mbf_tied', 'mbf_worried', 'mbf_calmed',
                 'mbf_fulfilling', 'mbf_produce', 'mbf_trouble', 'mbf_feel_like', 'mbf_enjoyed', 'mbf_anxious',
                 'mbf_confident', 'mbf_gained_weight', 'mbf_secure', 'mbf_fit_activities', 'mbf_relax', 'mbf_emotional',
                 'mbf_wonderful', 'mbf_score', 'mbf_comments', 'mw_mid', 'mw_interviewer', 'mw_interview_date',
                 'mw_infant_age', 'mw_assessment_type', 'mw_interest', 'mw_down', 'mw_sleep', 'mw_tired', 'mw_appetite',
                 'mw_bad', 'mw_conc', 'mw_move', 'mw_hurt', 'mw_score', 'mw_comments', 'cd_lat', 'cd_long',
                 'cd_confirm']]
            baseline = self.refine(baseline)
            day14 = df.loc[(df['redcap_event_name'] == "day_14_arm_1")][
                ['infant_id', 'redcap_event_name', 'lb_mid', 'lb_interviewer', 'lb_visit_date', 'lb_infant_age',
                 'lb_age_discharge', 'lb_assessment_type', 'lb_wchart', 'lb_lchart', 'lb_hchart', 'lb_weight_11',
                 'lb_weight_12', 'lb_weight_21', 'lb_weight_22', 'lb_weight_31', 'lb_weight_32', 'lb_weight_final',
                 'lb_length_11', 'lb_length_12', 'lb_length_21', 'lb_length_22', 'lb_length_31', 'lb_length_32',
                 'lb_length_final', 'lb_muac_11', 'lb_muac_12', 'lb_muac_21', 'lb_muac_22', 'lb_muac_31', 'lb_muac_32',
                 'lb_muac_final', 'lb_head_circum_11', 'lb_head_circum_12', 'lb_head_circum_21', 'lb_head_circum_22',
                 'lb_head_circum_31', 'lb_head_circum_32', 'lb_head_circum_final', 'lb_weight_gain', 'user_lbw',
                 'lb_comment']]
            month1 = df.loc[(df['redcap_event_name'] == "1st_month_arm_1")][
                ['infant_id', 'redcap_event_name', 'mb_date_1m', 'mb_problems_1m', 'mb_problems_spec_1m',
                 'mb_illness_times_1m', 'mb_addmitted_1m', 'mb_addmitted_spec_1m', 'mb_treated_times_1m',
                 'mb_treated_for_1m', 'mb_treated_for_spec_1m', 'mb_routine_times_1m', 'mb_routine_care_for_1m',
                 'mb_routine_visit_spec_1m', 'mb_assessment_next_1m', 'mb_comments_1m', 'lb_mid', 'lb_interviewer',
                 'lb_visit_date', 'lb_infant_age', 'lb_age_discharge', 'lb_assessment_type', 'lb_wchart', 'lb_lchart',
                 'lb_hchart', 'lb_weight_11', 'lb_weight_12', 'lb_weight_21', 'lb_weight_22', 'lb_weight_31',
                 'lb_weight_32', 'lb_weight_final', 'lb_length_11', 'lb_length_12', 'lb_length_21', 'lb_length_22',
                 'lb_length_31', 'lb_length_32', 'lb_length_final', 'lb_muac_11', 'lb_muac_12', 'lb_muac_21',
                 'lb_muac_22', 'lb_muac_31', 'lb_muac_32', 'lb_muac_final', 'lb_head_circum_11', 'lb_head_circum_12',
                 'lb_head_circum_21', 'lb_head_circum_22', 'lb_head_circum_31', 'lb_head_circum_32',
                 'lb_head_circum_final', 'lb_weight_gain', 'lb_bf_status', 'lb_bf_feeds_no', 'lb_bf_no_wet_diapers',
                 'lb_bf_no_soiled', 'lb_bf_nipples_comf', 'lb_still_breastfed', 'lb_drink_nipple', 'lb_drink_ors',
                 'lb_eat_vitamin', 'lb_other_liquids', 'lb_other_formular', 'lb_other_animal_fresh', 'lb_other_specify',
                 'lb_other_liquids_times', 'lb_foods_yesterday', 'lb_foods', 'lb_other_solid_spc', 'lb_yoghurt_times',
                 'lb_solid_times', 'lb_brestfeeding', 'lb_have_bf_difficulties', 'lb_bf_difficulties', 'lb_bf_times',
                 'lb_well_attached', 'lb_suckling', 'lb_breast_cond', 'lb_breast_cond_specify',
                 'lb_formular', 'lb_formular_spc', 'lb_formular_water_source', 'lb_formular_prepared',
                 'lb_formular_fed', 'lb_formular_consume', 'lb_have_feeding_diff', 'lb_feeding_difficulties',
                 'lb_formular_assessment', 'lb_feeding_assessment', 'lb_core_topics', 'lb_core_topics_spc', 'user_lbw',
                 'lb_comment', 'sa_mid', 'sa_bedtime', 'sa_sleep_room', 'sa_sleep_place', 'sa_wake_times', 'sa_wake',
                 'sa_sleep_mode', 'sa_sleep_well', 'sa_sleep_problem', 'sa_comments']]
            month2 = df.loc[(df['redcap_event_name'] == "2nd_month_arm_1")][
                ['infant_id', 'redcap_event_name', 'lb_interviewer', 'lb_mid', 'lb_visit_date', 'lb_infant_age',
                 'lb_age_discharge', 'lb_assessment_type', 'lb_wchart', 'lb_lchart', 'lb_hchart', 'lb_weight_11',
                 'lb_weight_12', 'lb_weight_21', 'lb_weight_22', 'lb_weight_31', 'lb_weight_32', 'lb_weight_final',
                 'lb_length_11', 'lb_length_12', 'lb_length_21', 'lb_length_22', 'lb_length_31', 'lb_length_32',
                 'lb_length_final', 'lb_muac_11', 'lb_muac_12', 'lb_muac_21', 'lb_muac_22', 'lb_muac_31', 'lb_muac_32',
                 'lb_muac_final', 'lb_head_circum_11', 'lb_head_circum_12', 'lb_head_circum_21', 'lb_head_circum_22',
                 'lb_head_circum_31', 'lb_head_circum_32', 'lb_head_circum_final', 'lb_weight_gain', 'lb_bf_status',
                 'lb_bf_feeds_no', 'lb_bf_no_wet_diapers', 'lb_bf_no_soiled', 'lb_bf_nipples_comf',
                 'lb_still_breastfed', 'lb_drink_nipple', 'lb_drink_ors', 'lb_eat_vitamin', 'lb_other_liquids',
                 'lb_other_formular', 'lb_other_animal_fresh', 'lb_other_specify', 'lb_other_liquids_times',
                 'lb_foods_yesterday', 'lb_foods', 'lb_other_solid_spc', 'lb_yoghurt_times', 'lb_solid_times',
                 'lb_brestfeeding', 'lb_have_bf_difficulties', 'lb_bf_difficulties', 'lb_bf_times', 'lb_well_attached',
                 'lb_suckling', 'lb_breast_cond', 'lb_breast_cond_specify', 'lb_formular', 'lb_formular_spc',
                 'lb_formular_water_source', 'lb_formular_prepared', 'lb_formular_fed', 'lb_formular_consume',
                 'lb_have_feeding_diff', 'lb_feeding_difficulties', 'lb_formular_assessment', 'lb_feeding_assessment',
                 'lb_core_topics', 'lb_core_topics_spc', 'user_lbw', 'lb_comment']]
            month3 = df.loc[(df['redcap_event_name'] == "3rd_month_arm_1")][
                ['infant_id', 'redcap_event_name', 'mb_date_3m', 'mb_illness_3m', 'mb_illness_spec_3m',
                 'mb_illness_any_3m', 'mb_illness_type_3m', 'mb_illness_oth_spec_3m', 'mb_outpt_visits_3m',
                 'mb_outpt_type_3m', 'mb_outpt_oth_spec_3m', 'mb_routine_3m', 'mb_routine_type_3m',
                 'mb_routine_spec_3m', 'mb_assessment_next_3m', 'mb_comments_3m', 'user_nt', 'nt_grains',
                 'nt_grains_times', 'nt_vitamins_vg', 'nt_vitamins_vg_times', 'nt_tubers', 'nt_tubers_times',
                 'nt_leafy', 'nt_leafy_times', 'nt_vegs', 'nt_vegs_times', 'nt_vitamins_ft', 'nt_vitamins_ft_times',
                 'nt_fruits', 'nt_fruits_times', 'nt_organs', 'nt_organs_times', 'nt_meats', 'nt_meats_times',
                 'nt_eggs', 'nt_eggs_times', 'nt_fish', 'nt_fish_times', 'nt_legumes', 'nt_legumes_times', 'nt_milk',
                 'nt_milk_times', 'nt_oils', 'nt_oils_times', 'nt_sweets', 'nt_sweets_times', 'nt_sugar',
                 'nt_sugar_times', 'nt_condiments', 'nt_condiments_times', 'nt_comments', 'mbf_mid', 'mbf_interviewer',
                 'mbf_interview_date', 'mbf_infant_age', 'mbf_assessment_type', 'mbf_inner_satisfaction',
                 'mbf_special_moments', 'mbf_interest_breastfeed', 'mbf_loved_breastfeed', 'mbf_burden_source',
                 'mbf_connected', 'mbf_suckled', 'mbf_exhausting', 'mbf_important_breastfeed', 'mbf_growth',
                 'mbf_worked', 'mbf_nurturing', 'mbf_conscious', 'mbf_tied', 'mbf_worried', 'mbf_calmed',
                 'mbf_fulfilling', 'mbf_produce', 'mbf_trouble', 'mbf_feel_like', 'mbf_enjoyed', 'mbf_anxious',
                 'mbf_confident', 'mbf_gained_weight', 'mbf_secure', 'mbf_fit_activities', 'mbf_relax', 'mbf_emotional',
                 'mbf_wonderful', 'mbf_score', 'mbf_comments', 'lb_mid', 'lb_interviewer', 'lb_visit_date',
                 'lb_age_discharge', 'lb_infant_age', 'lb_assessment_type', 'lb_wchart', 'lb_lchart', 'lb_hchart',
                 'lb_weight_11', 'lb_weight_12', 'lb_weight_21', 'lb_weight_22', 'lb_weight_31', 'lb_weight_32',
                 'lb_weight_final', 'lb_length_11', 'lb_length_12', 'lb_length_21', 'lb_length_22', 'lb_length_31',
                 'lb_length_32', 'lb_length_final', 'lb_muac_11', 'lb_muac_12', 'lb_muac_21', 'lb_muac_22',
                 'lb_muac_31', 'lb_muac_32', 'lb_muac_final', 'lb_head_circum_11', 'lb_head_circum_12',
                 'lb_head_circum_21', 'lb_head_circum_22', 'lb_head_circum_31', 'lb_head_circum_32',
                 'lb_head_circum_final',
                 'lb_weight_gain', 'lb_bf_status', 'lb_bf_feeds_no', 'lb_bf_no_wet_diapers', 'lb_bf_no_soiled',
                 'lb_bf_nipples_comf', 'lb_still_breastfed', 'lb_drink_nipple', 'lb_drink_ors', 'lb_eat_vitamin',
                 'lb_other_liquids', 'lb_other_formular', 'lb_other_animal_fresh', 'lb_other_specify',
                 'lb_other_liquids_times', 'lb_foods_yesterday', 'lb_foods', 'lb_other_solid_spc', 'lb_yoghurt_times',
                 'lb_solid_times', 'lb_brestfeeding', 'lb_have_bf_difficulties', 'lb_bf_difficulties', 'lb_bf_times',
                 'lb_well_attached', 'lb_suckling', 'lb_breast_cond', 'lb_breast_cond_specify', 'lb_formular',
                 'lb_formular_spc', 'lb_formular_water_source', 'lb_formular_prepared', 'lb_formular_fed',
                 'lb_formular_consume', 'lb_have_feeding_diff', 'lb_feeding_difficulties', 'lb_formular_assessment',
                 'lb_feeding_assessment', 'lb_core_topics', 'lb_core_topics_spc', 'user_lbw', 'lb_comment', 'mw_mid',
                 'mw_interviewer', 'mw_interview_date', 'mw_infant_age', 'mw_assessment_type', 'mw_interest', 'mw_down',
                 'mw_sleep', 'mw_tired', 'mw_appetite', 'mw_bad', 'mw_conc', 'mw_move', 'mw_hurt', 'mw_score',
                 'mw_comments', 'sa_mid', 'sa_bedtime', 'sa_sleep_room', 'sa_sleep_place', 'sa_wake_times', 'sa_wake',
                 'sa_sleep_mode', 'sa_sleep_well', 'sa_sleep_problem', 'sa_comments']]
            month3 = self.refine(month3)
            month4 = df.loc[(df['redcap_event_name'] == "4th_month_arm_1")][
                ['infant_id', 'redcap_event_name', 'lb_interviewer', 'lb_mid', 'lb_visit_date', 'lb_infant_age',
                 'lb_age_discharge', 'lb_assessment_type', 'lb_wchart', 'lb_lchart', 'lb_hchart', 'lb_weight_11',
                 'lb_weight_12', 'lb_weight_21', 'lb_weight_22', 'lb_weight_31', 'lb_weight_32', 'lb_weight_final',
                 'lb_length_11', 'lb_length_12', 'lb_length_21', 'lb_length_22', 'lb_length_31', 'lb_length_32',
                 'lb_length_final', 'lb_muac_11', 'lb_muac_12', 'lb_muac_21', 'lb_muac_22', 'lb_muac_31', 'lb_muac_32',
                 'lb_muac_final', 'lb_head_circum_11', 'lb_head_circum_12', 'lb_head_circum_21', 'lb_head_circum_22',
                 'lb_head_circum_31', 'lb_head_circum_32', 'lb_head_circum_final', 'lb_weight_gain', 'lb_bf_status',
                 'lb_bf_feeds_no', 'lb_bf_no_wet_diapers', 'lb_bf_no_soiled', 'lb_bf_nipples_comf',
                 'lb_still_breastfed', 'lb_drink_nipple', 'lb_drink_ors', 'lb_eat_vitamin', 'lb_other_liquids',
                 'lb_other_formular', 'lb_other_animal_fresh', 'lb_other_specify', 'lb_other_liquids_times',
                 'lb_foods_yesterday', 'lb_foods', 'lb_other_solid_spc', 'lb_yoghurt_times', 'lb_solid_times',
                 'lb_brestfeeding', 'lb_have_bf_difficulties', 'lb_bf_difficulties', 'lb_bf_times', 'lb_well_attached',
                 'lb_suckling', 'lb_breast_cond', 'lb_breast_cond_specify', 'lb_formular', 'lb_formular_spc',
                 'lb_formular_water_source', 'lb_formular_prepared', 'lb_formular_fed', 'lb_formular_consume',
                 'lb_have_feeding_diff', 'lb_feeding_difficulties', 'lb_formular_assessment', 'lb_feeding_assessment',
                 'lb_core_topics', 'lb_core_topics_spc', 'user_lbw', 'lb_comment']]
            month5 = df.loc[(df['redcap_event_name'] == "5th_month_arm_1")][
                ['infant_id', 'redcap_event_name', 'lb_interviewer', 'lb_mid', 'lb_visit_date', 'lb_infant_age',
                 'lb_age_discharge', 'lb_assessment_type', 'lb_wchart', 'lb_lchart', 'lb_hchart', 'lb_weight_11',
                 'lb_weight_12', 'lb_weight_21', 'lb_weight_22', 'lb_weight_31', 'lb_weight_32', 'lb_weight_final',
                 'lb_length_11', 'lb_length_12', 'lb_length_21', 'lb_length_22', 'lb_length_31', 'lb_length_32',
                 'lb_length_final', 'lb_muac_11', 'lb_muac_12', 'lb_muac_21', 'lb_muac_22', 'lb_muac_31', 'lb_muac_32',
                 'lb_muac_final', 'lb_head_circum_11', 'lb_head_circum_12', 'lb_head_circum_21', 'lb_head_circum_22',
                 'lb_head_circum_31', 'lb_head_circum_32', 'lb_head_circum_final', 'lb_weight_gain', 'lb_bf_status',
                 'lb_bf_feeds_no', 'lb_bf_no_wet_diapers', 'lb_bf_no_soiled', 'lb_bf_nipples_comf',
                 'lb_still_breastfed', 'lb_drink_nipple', 'lb_drink_ors', 'lb_eat_vitamin', 'lb_other_liquids',
                 'lb_other_formular', 'lb_other_animal_fresh', 'lb_other_specify', 'lb_other_liquids_times',
                 'lb_foods_yesterday', 'lb_foods', 'lb_other_solid_spc', 'lb_yoghurt_times', 'lb_solid_times',
                 'lb_brestfeeding', 'lb_have_bf_difficulties', 'lb_bf_difficulties', 'lb_bf_times', 'lb_well_attached',
                 'lb_suckling', 'lb_breast_cond', 'lb_breast_cond_specify', 'lb_formular', 'lb_formular_spc',
                 'lb_formular_water_source', 'lb_formular_prepared', 'lb_formular_fed', 'lb_formular_consume',
                 'lb_have_feeding_diff', 'lb_feeding_difficulties', 'lb_formular_assessment', 'lb_feeding_assessment',
                 'lb_core_topics', 'lb_core_topics_spc', 'user_lbw', 'lb_comment']]
            month6 = df.loc[(df['redcap_event_name'] == "6th_month_arm_1")][
                ['infant_id', 'redcap_event_name', 'mb_date_6m', 'mb_problems_6m', 'mb_problems_spec_6m',
                 'mb_illness_times_6m', 'mb_illness_type_6m', 'mb_illness_spec_6m', 'mb_outpt_times_6m',
                 'mb_outpt_type_6m', 'mb_outpt_spec_6m', 'mb_routine_times_6m', 'mb_routine_type_6m',
                 'mb_routine_spec_6m', 'mb_comments_6m', 'user_nt', 'nt_grains', 'nt_grains_times', 'nt_vitamins_vg',
                 'nt_vitamins_vg_times', 'nt_tubers', 'nt_tubers_times', 'nt_leafy', 'nt_leafy_times', 'nt_vegs',
                 'nt_vegs_times', 'nt_vitamins_ft', 'nt_vitamins_ft_times', 'nt_fruits', 'nt_fruits_times', 'nt_organs',
                 'nt_organs_times', 'nt_meats', 'nt_meats_times', 'nt_eggs', 'nt_eggs_times', 'nt_fish',
                 'nt_fish_times', 'nt_legumes', 'nt_legumes_times', 'nt_milk', 'nt_milk_times', 'nt_oils',
                 'nt_oils_times', 'nt_sweets', 'nt_sweets_times', 'nt_sugar', 'nt_sugar_times', 'nt_condiments',
                 'nt_condiments_times', 'nt_comments', 'mbf_mid', 'mbf_interviewer', 'mbf_interview_date',
                 'mbf_infant_age', 'mbf_assessment_type', 'mbf_inner_satisfaction', 'mbf_special_moments',
                 'mbf_interest_breastfeed', 'mbf_loved_breastfeed', 'mbf_burden_source', 'mbf_connected', 'mbf_suckled',
                 'mbf_exhausting', 'mbf_important_breastfeed', 'mbf_growth', 'mbf_worked', 'mbf_nurturing',
                 'mbf_conscious', 'mbf_tied', 'mbf_worried', 'mbf_calmed', 'mbf_fulfilling', 'mbf_produce',
                 'mbf_trouble', 'mbf_feel_like', 'mbf_enjoyed', 'mbf_anxious', 'mbf_confident', 'mbf_gained_weight',
                 'mbf_secure', 'mbf_fit_activities', 'mbf_relax', 'mbf_emotional', 'mbf_wonderful', 'mbf_score',
                 'mbf_comments',
                 'lb_interviewer', 'lb_mid', 'lb_visit_date', 'lb_age_discharge', 'lb_infant_age', 'lb_assessment_type',
                 'lb_wchart', 'lb_lchart', 'lb_hchart', 'lb_weight_11', 'lb_weight_12', 'lb_weight_21', 'lb_weight_22',
                 'lb_weight_31', 'lb_weight_32', 'lb_weight_final', 'lb_length_11', 'lb_length_12', 'lb_length_21',
                 'lb_length_22', 'lb_length_31', 'lb_length_32', 'lb_length_final', 'lb_muac_11', 'lb_muac_12',
                 'lb_muac_21', 'lb_muac_22', 'lb_muac_31', 'lb_muac_32', 'lb_muac_final', 'lb_head_circum_11',
                 'lb_head_circum_12', 'lb_head_circum_21', 'lb_head_circum_22', 'lb_head_circum_31',
                 'lb_head_circum_32', 'lb_head_circum_final', 'lb_weight_gain', 'lb_bf_status', 'lb_bf_feeds_no',
                 'lb_bf_no_wet_diapers', 'lb_bf_no_soiled', 'lb_bf_nipples_comf', 'lb_still_breastfed',
                 'lb_drink_nipple', 'lb_drink_ors', 'lb_eat_vitamin', 'lb_other_liquids', 'lb_other_formular',
                 'lb_other_animal_fresh', 'lb_other_specify', 'lb_other_liquids_times', 'lb_foods_yesterday',
                 'lb_foods', 'lb_other_solid_spc', 'lb_yoghurt_times', 'lb_solid_times', 'lb_brestfeeding',
                 'lb_have_bf_difficulties', 'lb_bf_difficulties', 'lb_bf_times', 'lb_well_attached', 'lb_suckling',
                 'lb_breast_cond', 'lb_breast_cond_specify', 'lb_formular', 'lb_formular_spc',
                 'lb_formular_water_source', 'lb_formular_prepared', 'lb_formular_fed', 'lb_formular_consume',
                 'lb_have_feeding_diff', 'lb_feeding_difficulties', 'lb_formular_assessment', 'lb_feeding_assessment',
                 'lb_core_topics', 'lb_core_topics_spc', 'user_lbw', 'lb_comment', 'gn_mid', 'user_gn',
                 'gn_facility', 'gn_assessment_date', 'gn_assessor_id', 'gn_child_sex', 'gn_child_dob', 'gn_age_months',
                 'gn_consent_assessment', 'gn_detail', 'gn_unwell', 'gn_weight_1st', 'gn_weight_2nd', 'gn_length_1st',
                 'gn_length_2nd', 'gn_length_measure', 'gn_head_circum_1st', 'gn_head_circum_2nd', 'gn_muac_1st',
                 'gn_muac_2nd', 'gn_comments', 'gm1_yn', 'gm2_yn', 'gm3_yn', 'gm4_yn', 'gm5_yn', 'gm6_yn', 'gm7_yn',
                 'gm8_yn', 'gm9_yn', 'gm10_yn', 'gm11_yn', 'gm12_yn', 'gm13_yn', 'gm14_yn', 'gm15_yn', 'gm16_yn',
                 'gm17_yn', 'gm18_yn', 'gm19_yn', 'gm20_yn', 'gm21_yn', 'gm22_yn', 'gm23_yn', 'gm24_yn', 'gm25_yn',
                 'gm26_yn', 'gm27_yn', 'gm28_yn', 'gm29_yn', 'gm30_yn', 'gm31_yn', 'gm32_yn', 'gm33_yn', 'gm34_yn',
                 'gm35_yn', 'gm36_yn', 'fm1_yn', 'fm2_yn', 'fm3_yn', 'fm4_yn', 'fm5_yn', 'fm6_yn', 'fm7_yn', 'fm8_yn',
                 'fm9_yn', 'fm10_yn', 'fm11_yn', 'fm12_yn', 'fm13_yn', 'fm14_yn', 'fm15_yn', 'fm16_yn', 'fm17_yn',
                 'fm18_yn', 'fm19_yn', 'fm20_yn', 'fm21_yn', 'fm22_yn', 'fm23_yn', 'fm24_yn', 'fm25_yn', 'fm26_yn',
                 'fm27_yn', 'fm28_yn', 'fm29_yn', 'fm30_yn', 'fm31_yn', 'fm32_yn', 'fm33_yn', 'fm34_yn', 'fm35_yn',
                 'fm36_yn', 'el1_yn', 'el2_yn', 'el3_yn', 'el4_yn', 'el5_yn', 'el6_yn', 'el7_yn', 'el8_yn', 'el9_yn',
                 'el10_yn', 'el11_yn', 'el12_yn', 'el13_yn', 'el14_yn', 'el15_yn', 'el16_yn', 'el17_yn', 'el18_yn',
                 'el19_yn', 'el20_yn', 'el21_yn', 'el22_yn', 'el23_yn', 'el24_yn', 'el25_yn', 'el26_yn', 'el27_yn',
                 'el28_yn', 'el29_yn', 'el30_yn', 'el31_yn', 'el32_yn', 'el33_yn', 'el34_yn', 'el35_yn', 'el36_yn',
                 'se1_yn', 'se2_yn', 'se3_yn', 'se4_yn', 'se5_yn', 'se6_yn', 'se7_yn',
                 'se8_yn', 'se9_yn', 'se10_yn', 'se11_yn', 'se12_yn', 'se13_yn', 'se14_yn', 'se15_yn', 'se16_yn',
                 'se17_yn', 'se18_yn', 'se19_yn', 'se20_yn', 'se21_yn', 'se22_yn', 'se23_yn', 'se24_yn', 'se25_yn',
                 'se26_yn', 'se27_yn', 'se28_yn', 'se29_yn', 'se30_yn', 'se31_yn', 'se32_yn', 'se33_yn', 'se34_yn',
                 'se35_yn', 'se36_yn', 'comment', 'ext_interviewer', 'ext_visit_date', 'ext_infant_age',
                 'ext_baby_warm', 'ext_baby_warmth_advice', 'ext_baby_warmth_other', 'ext_baby_clean',
                 'ext_baby_cleaning_advice', 'ext_baby_cleaning_other', 'ext_breastfeeding', 'ext_feeding_baby',
                 'ext_feeding_baby_other', 'ext_baby_feeds', 'ext_baby_feeds_other', 'ext_feeding_method',
                 'ext_feeding_method_other', 'ext_often_feed_baby', 'ext_hiv_pos_transmission', 'ext_hiv_trans_info',
                 'ext_baby_immunization', 'ext_breathing_problems', 'ext_diff_brestfeding_help', 'ext_fever_help',
                 'ext_cold_touch_help', 'ext_convulsions_help', 'ext_jaundice_help', 'ext_eye_help',
                 'ext_umbilical_cord_help', 'ext_postnatal_visits', 'ext_dist_health_fac', 'ext_mode_of_transport',
                 'ext_transport_other', 'ext_distance_nearest_fac', 'ext_postnatal_payment', 'ext_amount_paid',
                 'ext_postnatal_affordable', 'ext_payment_public_hf', 'ext_hc_payment', 'ext_hc_amount',
                 'ext_hc_affordable', 'ext_hc_public', 'ext_problem_after_discha', 'ext_problems_number',
                 'ext_problems_list', 'ext_problems_list_other', 'ext_problems_hc', 'ext_medcare_decision',
                 'ext_medcare_decision_other', 'ext_comments', 'mw_mid', 'mw_interviewer', 'mw_interview_date',
                 'mw_infant_age',
                 'mw_assessment_type', 'mw_interest', 'mw_down', 'mw_sleep', 'mw_tired', 'mw_appetite', 'mw_bad',
                 'mw_conc', 'mw_move', 'mw_hurt', 'mw_score', 'mw_comments', 'sa_mid', 'sa_bedtime', 'sa_sleep_room',
                 'sa_sleep_place', 'sa_wake_times', 'sa_wake', 'sa_sleep_mode', 'sa_sleep_well', 'sa_sleep_problem',
                 'sa_comments']]
            month6 = self.refine(month6)
            withd = df.loc[(df['redcap_event_name'] == "withdrawal_arm_1")][
                ['infant_id', 'redcap_event_name', 'wd_user', 'wd_interviewer', 'wd_date', 'wd_withdraw', 'wd_reason',
                 'wd_oth_spc', 'wd_data', 'wd_mid']]

            print("Splitting of master file finished successfully")
            return baseline, day14, month1, month2, month3, month4, month5, month6, withd
        except Exception as e:
            print("Error returning: {}".format(e))
            return pd.DataFrame([]), pd.DataFrame([]), pd.DataFrame([]), pd.DataFrame([]), pd.DataFrame(
                []), pd.DataFrame([]), pd.DataFrame([]), pd.DataFrame([]), pd.DataFrame([])

    def baseline(self, data):
        if data.empty:
            return pd.DataFrame([])
        else:
            ds = data.copy()
            bls = []
            ds['Form'] = "Baseline"
            ds.loc[(ds.bs_facility.isna()) | (ds.bs_mid.isna()) | (ds.unit_code_number.isna()) | (
                ds.enrollment_date.isna()) | (ds.infant_initals.isna()) | (ds.infant_dob.isna()) | (
                       ds.child_sex.isna()) | (ds.infant_single_twin_tri.isna()) | (
                               (ds.infant_single_twin_tri > 1) & (ds.first_enl.isna())) | (ds.cg_initials.isna()) | (
                       ds.cg_dob.isna()) | (ds.cg_infant_rship.isna()) | (ds.cg_residence.isna()) | (
                               (ds.cg_contact.isna()) & (ds.cg_contact_dk.str.startswith("['']"))) |
                   ((ds.cg_contact_alt.isna()) & (ds.cg_contact_alt_dk.str.startswith("['']"))) | (
                       ds.mt_adm_date.isna()) | (ds.mt_dsc_date.isna()) | (ds.ethnicity.isna()) | (
                       ds.religion.isna()) | (ds.marital_status.isna()) | (ds.education_level.isna()) |
                   (ds.income_source.isna()) | ((ds.income_source == 77) & (ds.income_source_other.isna())) | (
                       ds.household_number.isna()) | (ds.children_less15yrs.isna()) | (ds.people_15_64.isna()) | (
                       ds.people_over_65yrs.isna()) | (ds.children_care.str.startswith("['']")) | (
                       ds.hh_head.isna()) | (ds.first_pregnancy.isna()) | (ds.breastfeeding_start.isna()) | (
                       ds.difficulty_feeding.isna()) | (ds.feed_not_be4_breastmilk.isna()) | (
                       ds.baby_feeds.str.startswith("['']")) | (ds.feeding_method.str.startswith("['']")) |
                   (ds.kangaroo_mc_training.isna()) | (ds.baby_warmth_source.str.startswith("['']")) | (
                       ds.vitamin_k_after_birth.isna()) | (ds.bcg_polio.isna()) | (
                               (ds.cord_clean == 1) & (ds.cord_method.str.startswith("['']"))) | (
                       ds.proper_cord_care_info.isna()) | (ds.cord_cleaning_conf.isna()) | (
                       ds.antenal_visits_no.isna()) | (ds.distance_to_health_fac.isna()) | (
                       ds.mode_of_transport.str.startswith("['']")) | (ds.distance_nearest_fac.isna()) | (
                       ds.anc_payment.isna()) |
                   (ds.cwc_service_payment.isna()) | (ds.medical_care.isna()) | (ds.baby_warm_knowledge.isna()) | (
                       ds.baby_clean_knowledge.isna()) | (ds.breastfeeding_knowledge.isna()) | (
                       ds.hiv_pos_transmission.isna()) | (
                               (ds.hiv_pos_transmission == 1) & (ds.hiv_trans_info.str.startswith("['']"))) | (
                               (ds.hiv_trans_info.str.contains('77')) & (ds.hiv_trans_info_other.isna())) | (
                       ds.baby_immunization_info.isna()) | (ds.breathing_problems_help.isna()) | (
                       ds.dificulty_brestfeding_help.isna()) | (ds.fever_help.isna()) | (ds.cold_touch_help.isna()) |
                   (ds.convulsions_help.isna()) | (ds.jaundice_help.isna()) | (ds.eye_help.isna()) | (
                       ds.umbilical_cord_help.isna()) | (ds.delivery_location.isna()) | (
                       ds.labour_complications.isna()) | (ds.ga_at_birth.isna()) | (ds.apgar_score_1_min.isna()) | (
                       ds.apgar_score_5_min.isna()) | (ds.apgar_score_10_min.isna()) | (ds.breathing_support.isna()) | (
                       ds.mt_complications.str.startswith("['']")) | (ds.baby_admission_unit.isna()) |
                   ((ds.infant_single_twin_tri > 1) & (ds.twin_enl.isna())) | (
                               (ds.twin_enl == 1) & (ds.twin_enl_id.isna())) | (
                               (ds.twin_enl == 2) & (ds.twin_enl_reason.isna())) | (
                               (ds.infant_single_twin_tri > 2) & (ds.twin_enl_2.isna())) | (
                               (ds.twin_enl_2 == 1) & (ds.twin_enl_id_2.isna())) | (
                               (ds.twin_enl_2 == 2) & (ds.twin_enl_reason_2.isna())) | (
                               (ds.infant_single_twin_tri > 3) & (ds.twin_enl_3.isna())) | (
                               (ds.twin_enl_3 == 1) & (ds.twin_enl_id_3.isna())) | (
                               (ds.twin_enl_3 == 2) & (ds.twin_enl_reason_3.isna())) | (
                               (ds.cg_infant_rship == 77) & (ds.cg_infant_rship_other.isna())) |
                   ((ds.cg_infant_rship.notnull()) & (((ds.cg_infant_rship != 1) & (ds.infant_mother_alive.isna())) | (
                               (ds.cg_infant_rship != 2) & (ds.infant_father_alive.isna())))) | (
                               (ds.children_care.str.contains('77')) & (ds.children_care_other.isna())) | (
                               (ds.hh_head == 77) & (ds.hh_head_other.isna())) | (
                               (ds.hh_head.notnull() & (ds.hh_head != 2)) & (
                                   (ds.hh_head_infant_rship.isna()) | (ds.hh_head_educ_level.isna()) |
                                   (ds.hh_head_income_source.isna()))) | (
                               (ds.first_pregnancy == 0) & (ds.pregnant_times.isna())) | (
                               (ds.first_pregnancy == 0) & (ds.children_alive.isna())) | (((ds.first_pregnancy == 0) & (
                        (ds['pregnant_times'] - ds['children_alive'].fillna(0)) > 0)) & (ds.miscarriages.isna())) | (
                               (ds.miscarriages == 1) & (ds.miscarriages_number.isna())) | (((
                                                                                                         ds.first_pregnancy == 0) & (
                                                                                                         (
                                                                                                                     ds.pregnant_times -
                                                                                                                     ds[
                                                                                                                         'miscarriages_number'].fillna(
                                                                                                                         0)) > 0)) & (
                                                                                                ds.had_preterm.isna())) |
                   ((ds.had_preterm == 1) & (ds.preterm_no.isna())) | (((ds.first_pregnancy == 0) & ((ds[
                                                                                                          'pregnant_times'] - (
                                                                                                                  (ds[
                                                                                                                       'miscarriages_number'].fillna(
                                                                                                                      0)) + (
                                                                                                                      ds[
                                                                                                                          'children_alive'].fillna(
                                                                                                                          0)))) > 0)) & (
                                                                           ds.neodeath_first.isna())) | (
                               (ds.neodeath_first == 1) & (ds.neodeath_first_no.isna())) | (((ds[
                                                                                                  'first_pregnancy'] == 0) & (
                                                                                                         (ds[
                                                                                                              'pregnant_times'] - (
                                                                                                                      ds[
                                                                                                                          'children_alive'].fillna(
                                                                                                                          0) +
                                                                                                                      ds[
                                                                                                                          'miscarriages_number'].fillna(
                                                                                                                          0) +
                                                                                                                      ds[
                                                                                                                          'neodeath_first_no'].fillna(
                                                                                                                          0))) != 0)) & (
                                                                                                ds.neodeath_after.isna())) | (
                               (ds.neodeath_after == 1) & (ds.neodeath_after_no.isna())) | (
                               (ds.difficulty_feeding == 1) & (ds.difficulty_feeding_summary.isna())) | (
                               (ds.feed_not_be4_breastmilk == 1) & (ds.fluids_feeds_list.isna())) |
                   ((ds.baby_feeds.str.contains('77')) & (ds.baby_feeds_other.isna())) | (
                               (ds.feeding_method.str.contains('77')) & (ds.feeding_method_other.isna())) | (((
                                                                                                                  ds.feeding_method.str.contains(
                                                                                                                      '1')) | (
                                                                                                                  ds.feeding_method.str.contains(
                                                                                                                      '2')) | (
                                                                                                                  ds.feeding_method.str.contains(
                                                                                                                      '3'))) & (
                                                                                                                 ds.times_breastfed_24hrs.isna())) | (
                               (ds.kangaroo_mc_training == 1) & ((ds.kangaroo_mc_practice.isna()) |
                                                                 (ds.kangaroo_mc_challenges.str.startswith(
                                                                     "['']")))) | (
                               (ds.kangaroo_mc_challenges.str.contains('77')) & (
                           ds.kangaroo_mc_challenge_oth.isna())) | (
                               (ds.baby_warmth_source.str.contains('77')) & (ds.baby_warmth_source_other.isna())) | (
                               (ds.cord_method.str.contains('77')) & (ds.cord_method_other.isna())) | (
                               (ds.mode_of_transport.str.contains('77')) & (ds.mode_of_transport_other.isna())) | (
                               (ds.anc_payment == 1) & ((ds.amount_paid.isna()) | (ds.anc_affordable.isna()) | (
                           ds.anc_payment_public_hc.isna()))) |
                   ((ds.cwc_service_payment == 1) & (ds.cwc_public_hc.isna())) | (
                               (ds.medical_care == 77) & (ds.medical_care_other.isna())) | (
                               (ds.baby_warm_knowledge == 1) & (ds.baby_warmth_hm.str.startswith("['']"))) | (
                               (ds.baby_warmth_hm.str.contains("77")) & (ds.baby_warmth_hm_other.isna())) | (
                               (ds.baby_cleaning_advice_hm.str.contains('77')) & (
                           ds.baby_cleaning_advice_other.isna())) |
                   ((ds.breastfeeding_knowledge == 1) & (ds.feeding_baby_hm.str.startswith("['']"))) | (
                               (ds.feeding_baby_hm.str.contains('77')) & (ds.feeding_baby_hm_other.isna())) | (
                               (ds.delivery_location == 77) & (ds.delivery_location_other.isna())) | (
                               (ds.labour_complications == 1) & (
                           ds.labour_complications_list.str.startswith("['']"))) | (
                               (ds.labour_complications_list.str.contains('77')) & (
                           ds.labour_complications_other.isna())) |
                   ((ds.ga_at_birth > 1) & (ds.ga_by.isna())) | ((ds.ga_by == 77) & (ds.ga_by_other.isna())) | (
                               (ds.mt_complications.str.contains('77')) & (ds.mt_complications_other.isna())) | (
                               (ds.baby_admission_unit == 1) & (
                                   (ds.hc_facility_admitted.isna()) | (ds.days_baby_admitted.isna()) | (
                               ds.admission_reason.isna()) | (ds.baby_diagnosis.str.startswith("['']")))) |
                   ((ds.admission_reason == 77) & (ds.admission_reason_other.isna())) | (ds.cord_clean.isna()) | (
                               (ds.baby_admission_unit == 1) & ((ds.unit_admission_date.isna()) | (
                           ds.unit_discharge_date.isna()))), "Query"] = "Incomplete, Baseline"
            # ((ds.baby_diagnosis.str.contains('77'))&(ds.baby_diagnosis_other.isna()))
            bls.append(ds[ds.Query.notnull()][['infant_id', 'redcap_event_name', 'Form', 'Query', 'bs_interviewer']])
            ds.loc[((ds.baby_feeds.str.contains("1")) & (
                        (ds.baby_feeds.str.contains("2")) | (ds.baby_feeds.str.contains("3")) | (
                    ds.baby_feeds.str.contains("4")) | (ds.baby_feeds.str.contains("77")))) | (
                               (ds.baby_feeds.str.contains("4")) & (
                                   (ds.baby_feeds.str.contains("1")) | (ds.baby_feeds.str.contains("2")) | (
                               ds.baby_feeds.str.contains("3")) | (ds.baby_feeds.str.contains(
                               "77")))), 'Query1'] = "Invalid baby_feeds choices, Baseline D15"
            bls.append(self.rename_Q(
                ds[ds.Query1.notnull()][['infant_id', 'redcap_event_name', 'Form', 'Query1', 'bs_interviewer']]))
            ds.loc[(ds.kangaroo_mc_challenges.str.contains("6")) & ((ds.kangaroo_mc_challenges.str.contains("1")) | (
                ds.kangaroo_mc_challenges.str.contains("2")) | (ds.kangaroo_mc_challenges.str.contains("3")) | (
                                                                        ds.kangaroo_mc_challenges.str.contains("4")) | (
                                                                        ds.kangaroo_mc_challenges.str.contains(
                                                                            "5"))), "Query2"] = "Invalid kangaroo_mc_challenges, D18B"
            bls.append(self.rename_Q(
                ds[ds.Query2.notnull()][['infant_id', 'redcap_event_name', 'Form', 'Query2', 'bs_interviewer']]))
            ds.loc[(ds.baby_cleaning_advice_hm.str.contains("0")) & ((ds.baby_cleaning_advice_hm.str.contains("1")) | (
                ds.baby_cleaning_advice_hm.str.contains("2")) | (ds.baby_cleaning_advice_hm.str.contains("3")) | (
                                                                         ds.baby_cleaning_advice_hm.str.contains(
                                                                             "4")) | (
                                                                         ds.baby_cleaning_advice_hm.str.contains(
                                                                             "5")) | (
                                                                         ds.baby_cleaning_advice_hm.str.contains(
                                                                             "6")) | (
                                                                         ds.baby_cleaning_advice_hm.str.contains(
                                                                             "77"))), "Query3"] = "Invalid baby_cleaning_advice_hm, F33A"
            bls.append(self.rename_Q(
                ds[ds.Query3.notnull()][['infant_id', 'redcap_event_name', 'Form', 'Query3', 'bs_interviewer']]))
            return pd.concat(bls)

    def geocodes(self, data):
        if data.empty:
            return pd.DataFrame([])
        else:
            ds = data.copy()
            dls = []
            ds['Form'] = "Coordinates"
            ds.loc[(ds.cd_lat.isna()) | (ds.cd_long.isna()) | (
                ds.cd_confirm.str.startswith("['']")), 'Query'] = 'Missing/unconfirmed coordinates'
            dls.append(ds[ds.Query.notnull()][['infant_id', 'redcap_event_name', 'Form', 'Query', 'lb_interviewer']])
            return pd.concat(dls)

    def wealth_index(self, data):
        if data.empty:
            return pd.DataFrame([])
        else:
            ds = data.copy()
            dls = []
            ds['Form'] = "Wealth Index"
            ds.loc[(ds.wi_first == 1) & (
                        (ds.wi_house.isna()) | (ds.wi_pump.isna()) | (ds.wi_radio.isna()) | (ds.wi_tv.isna()) | (
                    ds.wi_watch.isna()) | (ds.wi_mobile.isna()) | (ds.wi_fridge.isna()) | (ds.wi_table.isna()) | (
                            ds.wi_chair.isna()) | (ds.wi_sofa.isna()) | (ds.wi_sponge_mat.isna()) | (
                            ds.wi_straw_mat.isna()) | (ds.wi_elec_stove.isna()) | (ds.wi_kero_lamp.isna()) | (
                            ds.we_press_lamp.isna()) | (ds.wi_kero_stove.isna()) |
                        (ds.wi_gas_stove.isna()) | (ds.wi_bike.isna()) | (ds.wi_motorcycle.isna()) | (
                            ds.wi_car.isna()) | (ds.wi_solar.isna()) | (ds.wi_mill.isna()) | (ds.wi_electric.isna()) | (
                            ds.wi_sew.isna()) | (ds.wi_coffee_land.isna()) | (ds.wi_comp.isna()) | (
                            ds.wi_bank.isna()) | (ds.wi_oxen.isna()) | (ds.wi_cow.isna()) | (ds.wi_calves.isna()) | (
                            ds.wi_bull.isna()) | (ds.wi_sheep_goat.isna()) | (ds.wi_horse.isna()) |
                        (ds.wi_chicken.isna()) | (ds.wi_bee_hive.isna()) | (ds.wi_land.isna()) | (
                            ds.wi_income_1.isna()) | (ds.wi_income_2.isna()) | (ds.wi_cook_loc.isna()) | (
                            ds.wi_fuel.isna()) | (ds.wi_roof.isna()) | (ds.wi_wall.isna()) | (ds.wi_floor.isna()) | (
                            ds.wi_sleep_rooms.isna()) | (ds.wi_house.isna()) | (ds.wi_pump.isna()) | (
                            ds.wi_radio.isna()) | (ds.wi_tv.isna()) | (ds.wi_watch.isna()) | (ds.wi_mobile.isna()) |
                        (ds.wi_fridge.isna()) | (ds.wi_table.isna()) | (ds.wi_chair.isna()) | (ds.wi_sofa.isna()) | (
                            ds.wi_sponge_mat.isna()) | (ds.wi_straw_mat.isna()) | (ds.wi_elec_stove.isna()) | (
                            ds.wi_kero_lamp.isna()) | (ds.we_press_lamp.isna()) | (ds.wi_kero_stove.isna()) | (
                            ds.wi_gas_stove.isna()) | (ds.wi_bike.isna()) | (ds.wi_motorcycle.isna()) | (
                            ds.wi_car.isna()) | (ds.wi_solar.isna()) | (ds.wi_mill.isna()) |
                        (ds.wi_electric.isna()) | (ds.wi_sew.isna()) | (ds.wi_coffee_land.isna()) | (
                            ds.wi_comp.isna()) | (ds.wi_bank.isna()) | (ds.wi_oxen.isna()) | (ds.wi_cow.isna()) | (
                            ds.wi_calves.isna()) | (ds.wi_bull.isna()) | (ds.wi_sheep_goat.isna()) | (
                            ds.wi_horse.isna()) | (ds.wi_chicken.isna()) | (ds.wi_bee_hive.isna()) | (
                            ds.wi_land.isna()) | (ds.wi_income_1.isna()) | (ds.wi_income_2.isna()) | (
                            ds.wi_cook_loc.isna()) |
                        (ds.wi_fuel.isna()) | (ds.wi_roof.isna()) | (ds.wi_wall.isna()) | (ds.wi_floor.isna()) | (
                            ds.wi_sleep_rooms.isna()) | ((ds.wi_land == 1) & (ds.wi_land_quant.isna())) | (
                                    (ds.wi_land_quant.notnull()) & (ds.wi_land_unit.isna())) | (
                                    (ds.wi_land_unit == 4) & (ds.wi_land_unit_other.isna())) | (
                                    (ds.wi_income_1 == 77) & (ds.wi_income_1_spc.isna())) | ((ds.wi_income_2 == 77) & (
                    ds.wi_income_2_spc.isna()))), "Query"] = "Incomplete, Wealth Index"
            dls.append(ds[ds.Query.notnull()][['infant_id', 'redcap_event_name', 'Form', 'Query', 'lb_interviewer']])
            return pd.concat(dls)

    def mbfes(self, data):
        if data.empty:
            return pd.DataFrame([])
        else:
            ds = data.copy()
            dls = []
            ds['Form'] = "Maternal Breastfeeding Evaluation Scale"
            ### missing data -> (ds.mbf_infant_age.isna())|
            ds.loc[(ds.mbf_mid.isna()) | (ds.mbf_interviewer.isna()) | (ds.mbf_interview_date.isna()) | (
                ds.mbf_assessment_type.isna()) | (ds.mbf_inner_satisfaction.isna()) | (
                       ds.mbf_special_moments.isna()) | (ds.mbf_interest_breastfeed.isna()) |
                   (ds.mbf_loved_breastfeed.isna()) | (ds.mbf_burden_source.isna()) | (ds.mbf_connected.isna()) | (
                       ds.mbf_suckled.isna()) | (ds.mbf_exhausting.isna()) | (ds.mbf_important_breastfeed.isna()) | (
                       ds.mbf_growth.isna()) | (ds.mbf_worked.isna()) | (ds.mbf_nurturing.isna()) | (
                       ds.mbf_conscious.isna()) |
                   (ds.mbf_tied.isna()) | (ds.mbf_worried.isna()) | (ds.mbf_calmed.isna()) | (
                       ds.mbf_fulfilling.isna()) | (ds.mbf_produce.isna()) | (ds.mbf_trouble.isna()) | (
                       ds.mbf_feel_like.isna()) | (ds.mbf_enjoyed.isna()) | (ds.mbf_anxious.isna()) | (
                       ds.mbf_confident.isna()) | (ds.mbf_gained_weight.isna()) |
                   (ds.mbf_secure.isna()) | (ds.mbf_fit_activities.isna()) | (ds.mbf_relax.isna()) | (
                       ds.mbf_emotional.isna()) | (ds.mbf_wonderful.isna()) | (
                       ds.mbf_score2.isna()), "Query"] = "Incomplete, Maternal Breastfeeding Evaluation"
            dls.append(ds[ds.Query.notnull()][['infant_id', 'redcap_event_name', 'Form', 'Query', 'lb_interviewer']])
            return pd.concat(dls)

    def phq9(self, data):
        if data.empty:
            return pd.DataFrame([])
        else:
            ds = data.copy()
            dls = []
            # missing data (ds.mw_infant_age.isna())|
            ds['Form'] = "Maternal Wellbeing Phq9"
            ds.loc[(ds.mw_interviewer.isna()) | (ds.mw_interview_date.isna()) | (ds.mw_assessment_type.isna()) |
                   (ds.mw_interest.isna()) | (ds.mw_down.isna()) | (ds.mw_sleep.isna()) | (ds.mw_tired.isna()) | (
                       ds.mw_appetite.isna()) |
                   (ds.mw_bad.isna()) | (ds.mw_conc.isna()) | (ds.mw_move.isna()) | (ds.mw_hurt.isna()) | (
                       ds.mw_score2.isna()), "Query"] = f"Incomplete, Maternal Wellbeing Phq9"
            dls.append(ds[ds.Query.notnull()][['infant_id', 'redcap_event_name', 'Form', 'Query', 'lb_interviewer']])
            return pd.concat(dls)

    def mobidity1(self, data):
        if data.empty:
            return pd.DataFrame([])
        else:
            ds = data.copy()
            dls = []
            ds['Form'] = "Infant morbidity assessment 1 month"
            ds.loc[(ds.mb_date_1m.isna()) | (ds.mb_problems_1m.str.startswith("['']")) | (
                ds.mb_illness_times_1m.isna()) | (ds.mb_treated_times_1m.isna()) | (ds.mb_routine_times_1m.isna()) | (
                               (ds.mb_problems_1m.str.contains('77')) & (ds.mb_problems_spec_1m.isna())) |
                   ((ds.mb_addmitted_1m.str.contains('77')) & (ds.mb_addmitted_spec_1m.isna())) | (((
                                                                                                                ds.mb_illness_times_1m != 0) & (
                                                                                                                ds.mb_illness_times_1m != 99) & (
                                                                                                        ds.mb_illness_times_1m.notnull())) & (
                                                                                                       ds.mb_addmitted_1m.str.startswith(
                                                                                                           "['']"))) |
                   (((ds.mb_treated_times_1m != 0) & (ds.mb_treated_times_1m != 99) & (
                       ds.mb_treated_times_1m.notnull())) & (ds.mb_treated_for_1m.str.startswith("['']"))) | (
                               (ds.mb_treated_for_1m.str.contains('77')) & (ds.mb_treated_for_spec_1m.isna())) |
                   (((ds.mb_routine_times_1m != 0) & (ds.mb_routine_times_1m != 99) & (
                       ds.mb_routine_times_1m.notnull())) & (ds.mb_routine_care_for_1m.str.startswith("['']"))) | (
                               (ds.mb_routine_care_for_1m.str.contains('77')) & (
                           ds.mb_routine_visit_spec_1m.isna())), "Query"] = "Incomplete, Infant Mobidity 1 Month"
            dls.append(ds[ds.Query.notnull()][['infant_id', 'redcap_event_name', 'Form', 'Query', 'lb_interviewer']])
            return pd.concat(dls)

    def mobidity3(self, data):
        if data.empty:
            return pd.DataFrame([])
        else:
            ds = data.copy()
            dls = []
            ds['Form'] = "Infant morbidity assessment 3 months"
            ds.loc[
                (ds.mb_date_3m.isna()) | (ds.mb_illness_3m.str.startswith("['']")) | (ds.mb_illness_any_3m.isna()) | (
                    ds.mb_outpt_visits_3m.isna()) | (ds.mb_routine_3m.isna()) | (ds.mb_assessment_next_3m.isna()) | (
                            (ds.mb_illness_3m.str.contains("77")) & (ds.mb_illness_spec_3m.isna())) |
                (((ds.mb_illness_any_3m != 0) & (ds.mb_illness_any_3m != 99) & (ds.mb_illness_any_3m.notnull())) & (
                    ds.mb_illness_type_3m.str.startswith("['']"))) | (
                            (ds.mb_illness_type_3m.str.contains("77")) & (ds.mb_illness_oth_spec_3m.isna())) |
                (((ds.mb_outpt_visits_3m != 0) & (ds.mb_outpt_visits_3m != 99) & (ds.mb_outpt_visits_3m.notnull())) & (
                    ds.mb_outpt_type_3m.str.startswith("['']"))) | (
                            (ds.mb_outpt_type_3m.str.contains("77")) & (ds.mb_outpt_oth_spec_3m.isna())) |
                (((ds.mb_routine_3m != 0) & (ds.mb_routine_3m != 99) & (ds.mb_routine_3m.notnull())) & (
                    ds.mb_routine_type_3m.str.startswith("['']"))) | ((ds.mb_routine_type_3m.str.contains("77")) & (
                    ds.mb_routine_spec_3m.isna())), "Query"] = "Incomplete, Infant Mobidity 3 Months"
            dls.append(ds[ds.Query.notnull()][['infant_id', 'redcap_event_name', 'Form', 'Query', 'lb_interviewer']])
            return pd.concat(dls)

    def mobidity6(self, data):
        if data.empty:
            return pd.DataFrame([])
        else:
            ds = data.copy()
            dls = []
            ds['Form'] = "Infant Morbidity Assessment 6 Months"
            ds.loc[(ds.mb_date_6m.isna()) | (ds.mb_problems_6m.str.startswith("['']")) | (
                ds.mb_illness_times_6m.isna()) | (ds.mb_outpt_times_6m.isna()) | (ds.mb_routine_times_6m.isna()) | (
                               (ds.mb_problems_6m.str.contains('77')) & (ds.mb_problems_spec_6m.isna())) |
                   (((ds.mb_illness_times_6m != 0) & (ds.mb_illness_times_6m != 99) & (
                       ds.mb_illness_times_6m.notnull())) & (ds.mb_illness_type_6m.str.startswith("['']"))) | (
                               (ds.mb_illness_type_6m.str.contains('77')) & (ds.mb_illness_spec_6m.isna())) |
                   (((ds.mb_outpt_times_6m != 0) & (ds.mb_outpt_times_6m != 99) & (ds.mb_outpt_times_6m.notnull())) & (
                       ds.mb_outpt_type_6m.str.startswith("['']"))) | (
                               (ds.mb_outpt_type_6m.str.contains('77')) & (ds.mb_outpt_spec_6m.isna())) |
                   (((ds.mb_routine_times_6m != 0) & (ds.mb_routine_times_6m != 99) & (
                       ds.mb_routine_times_6m.notnull())) & (ds.mb_routine_type_6m.str.startswith("['']"))) |
                   ((ds.mb_routine_type_6m.str.contains('77')) & (
                       ds.mb_routine_spec_6m.isna())), "Query"] = "Incomplete, Infant Mobidity 6 Months"
            dls.append(ds[ds.Query.notnull()][['infant_id', 'redcap_event_name', 'Form', 'Query', 'lb_interviewer']])
            return pd.concat(dls)

    def lbw(self, data):
        """
        """
        if data.empty:
            return pd.DataFrame([])
        else:
            ds = data.copy()
            dls = []
            ds['Form'] = "Lbw Follow Up"
            ds.loc[(ds.lb_interviewer.isna()) | (ds.lb_visit_date.isna()) | (ds.lb_infant_age.isna()) | (
                ds.lb_assessment_type.isna()) | (ds.lb_weight_11.isna()) | (ds.lb_weight_12.isna()) | (
                       ds.lb_weight_final.isna()) | (ds.lb_length_11.isna()) | (ds.lb_length_12.isna()) | (
                       ds.lb_length_final.isna()) | (ds.lb_muac_11.isna()) | (ds.lb_muac_12.isna()) | (
                       ds.lb_muac_final.isna()) | (ds.lb_head_circum_11.isna()) | (ds.lb_head_circum_12.isna()) | (
                       ds.lb_head_circum_final.isna()) | (ds.lb_weight_gain.isna()) | (ds.lb_bf_status.isna()) |
                   (ds.lb_bf_feeds_no.isna()) | (ds.lb_bf_no_wet_diapers.isna()) | (ds.lb_bf_no_soiled.isna()) | (
                       ds.lb_bf_nipples_comf.isna()) | (ds.lb_still_breastfed.isna()) | (ds.lb_drink_nipple.isna()) | (
                       ds.lb_drink_ors.isna()) | (ds.lb_eat_vitamin.isna()) | (ds.lb_foods_yesterday.isna()) | (
                               (ds.lb_other_liquids.str.contains('8')) & (ds.lb_formular.isna())) | (
                               (ds.lb_formular == 77) & (ds.lb_formular_spc.isna())) | (
                       ds.lb_formular_assessment.isna()) | (ds.lb_feeding_assessment.isna()) | (
                       ds.lb_other_liquids.str.startswith("['']")) | (
                               (ds.lb_other_liquids.str.contains('8')) & (ds.lb_other_formular.isna())) |
                   ((ds.lb_other_liquids.str.contains('10')) & (ds.lb_other_animal_fresh.isna())) | (
                               (ds.lb_foods.str.contains('16')) & (ds.lb_other_solid_spc.isna())) | (
                       ds.lb_core_topics.str.startswith("['']")) | (
                               (ds.lb_core_topics.str.contains('77')) & (ds.lb_core_topics_spc.isna())) |
                   (((ds.lb_weight_11 - ds.lb_weight_12) > 100) | ((ds.lb_weight_12 - ds.lb_weight_11) > 100)) & (
                               (ds.lb_weight_21.isna()) | (ds.lb_weight_22.isna())) | (
                               ((ds.lb_weight_21 - ds.lb_weight_22) > 100) | (
                                   (ds.lb_weight_22 - ds.lb_weight_21) > 100)) & (
                               (ds.lb_weight_31.isna()) | (ds.lb_weight_32.isna())) | (
                               ((ds.lb_length_11 - ds.lb_length_12) > 0.7) | (
                                   (ds.lb_length_12 - ds.lb_length_11) > 0.7)) & (
                               (ds.lb_length_21.isna()) | (ds.lb_length_22.isna())) | (
                               ((ds.lb_length_21 - ds.lb_length_22) > 0.7) |
                               ((ds.lb_length_22 - ds.lb_length_21) > 0.7)) & (
                               (ds.lb_length_31.isna()) | (ds.lb_length_32.isna())) | (
                               ((ds.lb_muac_11 - ds.lb_muac_12) > 5) | ((ds.lb_muac_12 - ds.lb_muac_11) > 5)) & (
                               (ds.lb_muac_21.isna()) | (ds.lb_muac_22.isna())) | (
                               ((ds.lb_muac_21 - ds.lb_muac_22) > 5) | ((ds.lb_muac_22 - ds.lb_muac_21) > 5)) & (
                               (ds.lb_muac_31.isna()) | (ds.lb_muac_32.isna())) | (
                               ((ds.lb_head_circum_11 - ds.lb_head_circum_12) > 0.5) |
                               ((ds.lb_head_circum_12 - ds.lb_head_circum_11) > 0.5)) & (
                               (ds.lb_head_circum_21.isna()) | (ds.lb_head_circum_22.isna())) | (
                               ((ds.lb_head_circum_21 - ds.lb_head_circum_22) > 0.5) | (
                                   (ds.lb_head_circum_22 - ds.lb_head_circum_21) > 0.5)) & (
                               (ds.lb_head_circum_31.isna()) | (ds.lb_head_circum_32.isna())) | (
                               (ds.lb_other_liquids.str.contains('11')) & (ds.lb_other_specify.isna())) |
                   (((ds.lb_other_liquids.str.contains('4')) | (ds.lb_other_liquids.str.contains('5')) | (
                       ds.lb_other_liquids.str.contains('6')) | (ds.lb_other_liquids.str.contains('7')) | (
                         ds.lb_other_liquids.str.contains('8')) | (ds.lb_other_liquids.str.contains('9')) | (
                         ds.lb_other_liquids.str.contains('10')) | (ds.lb_other_liquids.str.contains('11'))) & (
                        ds.lb_other_liquids_times.isna())) |
                   ((ds.lb_foods_yesterday == 2) & (ds.lb_foods.str.startswith("['']"))) | (
                               (ds.lb_foods.str.contains('1')) & (ds.lb_yoghurt_times.isna())) | (
                               (ds.lb_foods.str.contains('16')) & (ds.lb_solid_times.isna())) | (
                               (ds.lb_still_breastfed == 1) & (
                                   (ds.lb_have_bf_difficulties.isna()) | (ds.lb_bf_times.isna()) | (
                               ds.lb_well_attached.isna()) | (ds.lb_suckling.isna()) | (ds.lb_breast_cond.isna()))) | (
                               (ds.lb_have_bf_difficulties == 1) & (ds.lb_bf_difficulties.isna())) |
                   ((ds.lb_breast_cond == 1) & (ds.lb_breast_cond_specify.isna())) | ((ds.lb_formular.notnull()) & (
                        (ds.lb_formular_water_source.isna()) | (ds.lb_formular_prepared.isna()) | (
                    ds.lb_formular_fed.isna()) | (ds.lb_formular_consume.isna()) | (
                            ds.lb_have_feeding_diff.isna()))) | ((ds.lb_have_feeding_diff == 1) & (
                ds.lb_feeding_difficulties.isna())), "Query"] = "Incomplete, LBW follow-up"
            dls.append(ds[ds.Query.notnull()][['infant_id', 'redcap_event_name', 'Form', 'Query', 'lb_interviewer']])
            return pd.concat(dls)

    def lbw_1(self, data):
        if data.empty:
            return pd.DataFrame([])
        else:
            ds = data.copy()
            dls = []
            ds['Form'] = "Lbw Follow Up"
            ds.loc[(ds.lb_visit_date.isna()) | (ds.lb_infant_age.isna()) | (ds.lb_assessment_type.isna()) | (
                ds.lb_weight_11.isna()) | (ds.lb_weight_12.isna()) | (ds.lb_weight_final.isna()) | (
                       ds.lb_length_11.isna()) | (ds.lb_length_12.isna()) | (ds.lb_length_final.isna()) | (
                       ds.lb_muac_11.isna()) | (ds.lb_muac_12.isna()) | (ds.lb_muac_final.isna()) | (
                       ds.lb_head_circum_11.isna()) | (ds.lb_head_circum_12.isna()) | (
                       ds.lb_head_circum_final.isna()) | (ds.lb_weight_gain.isna()) |
                   (((ds.lb_weight_11 - ds.lb_weight_12) > 100) | ((ds.lb_weight_12 - ds.lb_weight_11) > 100)) & (
                               (ds.lb_weight_21.isna()) | (ds.lb_weight_22.isna())) | (
                               ((ds.lb_weight_21 - ds.lb_weight_22) > 100) | (
                                   (ds.lb_weight_22 - ds.lb_weight_21) > 100)) & (
                               (ds.lb_weight_31.isna()) | (ds.lb_weight_32.isna())) | (
                               ((ds.lb_length_11 - ds.lb_length_12) > 0.7) | (
                                   (ds.lb_length_12 - ds.lb_length_11) > 0.7)) & (
                               (ds.lb_length_21.isna()) | (ds.lb_length_22.isna())) | (
                               ((ds.lb_length_21 - ds.lb_length_22) > 0.7) |
                               ((ds.lb_length_22 - ds.lb_length_21) > 0.7)) & (
                               (ds.lb_length_31.isna()) | (ds.lb_length_32.isna())) | (
                               ((ds.lb_muac_11 - ds.lb_muac_12) > 5) | ((ds.lb_muac_12 - ds.lb_muac_11) > 5)) & (
                               (ds.lb_muac_21.isna()) | (ds.lb_muac_22.isna())) | (
                               ((ds.lb_muac_21 - ds.lb_muac_22) > 5) | ((ds.lb_muac_22 - ds.lb_muac_21) > 5)) & (
                               (ds.lb_muac_31.isna()) | (ds.lb_muac_32.isna())) | (
                               ((ds.lb_head_circum_11 - ds.lb_head_circum_12) > 0.5) |
                               ((ds.lb_head_circum_12 - ds.lb_head_circum_11) > 0.5)) & (
                               (ds.lb_head_circum_21.isna()) | (ds.lb_head_circum_22.isna())) | (
                               ((ds.lb_head_circum_21 - ds.lb_head_circum_22) > 0.5) | (
                                   (ds.lb_head_circum_22 - ds.lb_head_circum_21) > 0.5)) & (
                               (ds.lb_head_circum_31.isna()) | (
                           ds.lb_head_circum_32.isna())), "Query"] = "Incomplete, LBW follow-up"
            dls.append(ds[ds.Query.notnull()][['infant_id', 'redcap_event_name', 'Form', 'Query', 'lb_interviewer']])
            return pd.concat(dls)

    def MDAT(self, data):
        if data.empty:
            return pd.DataFrame([])
        else:
            dls = []
            fm = data.copy()
            fm['Form'] = 'FineMotor'
            fm['FineMotor_errors'] = 0
            fm.loc[(fm.fm1_yn.isna()) | (fm.fm2_yn.isna()) | (fm.fm3_yn.isna()) | (fm.fm4_yn.isna()) | (
                fm.fm5_yn.isna()) | (fm.fm6_yn.isna()) | (fm.fm7_yn.isna()) | (fm.fm8_yn.isna()) | (
                       fm.fm9_yn.isna()) | (fm.fm10_yn.isna()) | (fm.fm11_yn.isna()) |
                   (fm.fm12_yn.isna()) | (fm.fm13_yn.isna()) | (fm.fm13_yn.isna()) | (fm.fm14_yn.isna()) | (
                       fm.fm15_yn.isna()) | (fm.fm16_yn.isna()) | (fm.fm17_yn.isna()) | (fm.fm18_yn.isna()) | (
                       fm.fm18_yn.isna()) | (fm.fm19_yn.isna()) |
                   (fm.fm20_yn.isna()) | (fm.fm21_yn.isna()) | (fm.fm22_yn.isna()) | (fm.fm23_yn.isna()) | (
                       fm.fm24_yn.isna()) | (fm.fm25_yn.isna()) | (fm.fm26_yn.isna()) | (fm.fm27_yn.isna()) | (
                       fm.fm28_yn.isna()) | (fm.fm29_yn.isna()) |
                   (fm.fm30_yn.isna()) | (fm.fm31_yn.isna()) | (fm.fm31_yn.isna()) | (fm.fm32_yn.isna()) | (
                       fm.fm33_yn.isna()) | (fm.fm34_yn.isna()) | (fm.fm35_yn.isna()) | (
                       fm.fm36_yn.isna()), 'FineMotor_errors'] = 1
            # print(fm.FineMotor_errors.value_counts())
            dls.append(fm[fm.FineMotor_errors == 1][['infant_id', 'redcap_event_name', 'Form', 'lb_interviewer']])

            gm = data.copy()
            gm['Form'] = 'GrossMotor'
            gm['GrossMotor_errors'] = 0
            gm.loc[(gm.gm1_yn.isna()) | (gm.gm2_yn.isna()) | (gm.gm3_yn.isna()) | (gm.gm4_yn.isna()) | (
                gm.gm5_yn.isna()) | (gm.gm6_yn.isna()) | (gm.gm7_yn.isna()) | (gm.gm8_yn.isna()) | (
                       gm.gm9_yn.isna()) | (gm.gm10_yn.isna()) | (gm.gm11_yn.isna()) |
                   (gm.gm12_yn.isna()) | (gm.gm13_yn.isna()) | (gm.gm14_yn.isna()) | (gm.gm15_yn.isna()) | (
                       gm.gm16_yn.isna()) | (gm.gm17_yn.isna()) | (gm.gm18_yn.isna()) | (gm.gm19_yn.isna()) | (
                       gm.gm20_yn.isna()) | (gm.gm21_yn.isna()) |
                   (gm.gm22_yn.isna()) | (gm.gm23_yn.isna()) | (gm.gm24_yn.isna()) | (gm.gm25_yn.isna()) | (
                       gm.gm26_yn.isna()) | (gm.gm27_yn.isna()) | (gm.gm28_yn.isna()) | (gm.gm29_yn.isna()) | (
                       gm.gm30_yn.isna()) | (gm.gm31_yn.isna()) |
                   (gm.gm32_yn.isna()) | (gm.gm33_yn.isna()) | (gm.gm34_yn.isna()) | (gm.gm35_yn.isna()) | (
                       gm.gm36_yn.isna()), 'GrossMotor_errors'] = 1
            # print(gm.GrossMotor_errors.value_counts())
            dls.append(gm[gm.GrossMotor_errors == 1][['infant_id', 'redcap_event_name', 'Form', 'lb_interviewer']])

            lan = data.copy()
            lan['Form'] = 'Language'
            lan['Language_Errors'] = 0
            lan.loc[(lan.el1_yn.isna()) | (lan.el2_yn.isna()) | (lan.el3_yn.isna()) | (lan.el4_yn.isna()) | (
                lan.el5_yn.isna()) | (lan.el6_yn.isna()) | (lan.el7_yn.isna()) | (lan.el8_yn.isna()) | (
                        lan.el9_yn.isna()) | (lan.el10_yn.isna()) |
                    (lan.el11_yn.isna()) | (lan.el12_yn.isna()) | (lan.el13_yn.isna()) | (lan.el14_yn.isna()) | (
                        lan.el15_yn.isna()) | (lan.el16_yn.isna()) | (lan.el17_yn.isna()) | (lan.el18_yn.isna()) | (
                        lan.el19_yn.isna()) | (lan.el20_yn.isna()) |
                    (lan.el21_yn.isna()) | (lan.el22_yn.isna()) | (lan.el23_yn.isna()) | (lan.el24_yn.isna()) | (
                        lan.el25_yn.isna()) | (lan.el26_yn.isna()) | (lan.el27_yn.isna()) | (lan.el28_yn.isna()) | (
                        lan.el29_yn.isna()) | (lan.el30_yn.isna()) |
                    (lan.el31_yn.isna()) | (lan.el32_yn.isna()) | (lan.el33_yn.isna()) | (lan.el34_yn.isna()) | (
                        lan.el35_yn.isna()) | (lan.el36_yn.isna()), 'Language_Errors'] = 1
            # print(lan.Language_Errors.value_counts())
            dls.append(lan[lan.Language_Errors == 1][['infant_id', 'redcap_event_name', 'Form', 'lb_interviewer']])

            sep = data.copy()
            sep['Form'] = 'Social Emotional Play'
            sep['SocialEmotiona_errors'] = 0
            sep.loc[(sep.se1_yn.isna()) | (sep.se2_yn.isna()) | (sep.se3_yn.isna()) | (sep.se4_yn.isna()) | (
                sep.se5_yn.isna()) | (sep.se6_yn.isna()) | (sep.se7_yn.isna()) | (sep.se8_yn.isna()) | (
                        sep.se9_yn.isna()) | (sep.se10_yn.isna()) |
                    (sep.se10_yn.isna()) | (sep.se11_yn.isna()) | (sep.se12_yn.isna()) | (sep.se13_yn.isna()) | (
                        sep.se14_yn.isna()) | (sep.se15_yn.isna()) | (sep.se16_yn.isna()) | (sep.se17_yn.isna()) | (
                        sep.se18_yn.isna()) | (sep.se19_yn.isna()) |
                    (sep.se20_yn.isna()) | (sep.se21_yn.isna()) | (sep.se22_yn.isna()) | (sep.se23_yn.isna()) | (
                        sep.se24_yn.isna()) | (sep.se25_yn.isna()) | (sep.se26_yn.isna()) | (sep.se27_yn.isna()) | (
                        sep.se28_yn.isna()) | (sep.se29_yn.isna()) |
                    (sep.se30_yn.isna()) | (sep.se31_yn.isna()) | (sep.se32_yn.isna()) | (sep.se33_yn.isna()) | (
                        sep.se34_yn.isna()) | (sep.se35_yn.isna()) | (sep.se36_yn.isna()), 'SocialEmotiona_errors'] = 1
            # print(sep.SocialEmotiona_errors.value_counts())
            dls.append(
                sep[sep.SocialEmotiona_errors == 1][['infant_id', 'redcap_event_name', 'Form', 'lb_interviewer']])
            mdat = pd.concat(dls)
            mdat['Query'] = "Incomplete, MDAT"
            return mdat

    def exit(self, data):
        if data.empty:
            return pd.DataFrame([])
        else:
            ds = data.copy()
            ds['Form'] = "Exit form"
            dls = []
            ds.loc[(ds.ext_baby_warm.isna()) | (ds.ext_baby_clean.isna()) | (ds.ext_breastfeeding.isna()) | (
                ds.ext_often_feed_baby.isna()) |
                   (ds.ext_hiv_pos_transmission.isna()) | (ds.ext_hiv_trans_info.isna()) | (
                       ds.ext_baby_immunization.isna()) | (ds.ext_breathing_problems.isna()) | (
                       ds.ext_diff_brestfeding_help.isna()) | (ds.ext_fever_help.isna()) | (
                       ds.ext_cold_touch_help.isna()) | (ds.ext_convulsions_help.isna()) | (
                       ds.ext_jaundice_help.isna()) | (ds.ext_eye_help.isna()) | (ds.ext_umbilical_cord_help.isna()) | (
                       ds.ext_postnatal_visits.isna()) | (ds.ext_dist_health_fac.isna()) | (
                       ds.ext_distance_nearest_fac.isna()) |
                   (ds.ext_postnatal_payment.isna()) | (ds.ext_hc_payment.isna()) | (
                       ds.ext_problem_after_discha.isna()) | (ds.ext_medcare_decision.isna()) | (
                       ds.ext_interviewer.isna()) | (ds.ext_visit_date.isna()) | (
                       ds.ext_baby_feeds.str.startswith("['']")) | (ds.ext_feeding_method.str.startswith("['']")) | (
                       ds.ext_mode_of_transport.str.startswith("['']")) | (
                               (ds.ext_baby_warm == 1) & (ds.ext_baby_warmth_advice.str.startswith("['']"))) | (
                               (ds.ext_baby_warmth_advice.str.contains('77')) & (ds.ext_baby_warmth_other.isna())) |
                   ((ds.ext_baby_clean == 1) & (ds.ext_baby_cleaning_advice.str.startswith("['']"))) | (
                               (ds.ext_baby_cleaning_advice.str.contains('77')) & (
                           ds.ext_baby_cleaning_other.isna())) | (
                               (ds.ext_breastfeeding == 1) & (ds.ext_feeding_baby.str.startswith("['']"))) | (
                               (ds.ext_feeding_baby.str.contains('77')) & (ds.ext_feeding_baby_other.isna())) | (
                               (ds.ext_baby_feeds.str.contains('77')) & (ds.ext_baby_feeds_other.isna())) | (
                               (ds.ext_feeding_method.str.contains('77')) & (
                           ds.ext_feeding_method_other.isna())), 'Query'] = "Incomplete exit form"
            dls.append(ds[ds.Query.notnull()][['infant_id', 'redcap_event_name', 'Form', 'Query', 'lb_interviewer']])
            return pd.concat(dls)

    def wdaw(self, data):
        if data.empty:
            return pd.DataFrame([])
        else:
            ds = data.copy()
            ds['Form'] = "Withdrawal form"
            dls = []
            ds.loc[(ds.wd_interviewer.isna()) | (ds.wd_date.isna()) | (ds.wd_withdraw.isna()) | (
                        (ds.wd_withdraw == 1) & (ds.wd_reason.str.startswith("['']"))) | (
                               (ds.wd_reason.str.contains('77')) & (ds.wd_oth_spc.isna())) | (
                       ds.wd_data.isna()), 'Query'] = "Missing/incomplete withdrawal form"
            dls.append(ds[ds.Query.notnull()][['infant_id', 'redcap_event_name', 'Form', 'Query', 'lb_interviewer']])
            return pd.concat(dls)

    def refine_queries(self, dat, write=False):
        """Compiles of all reports for every event into a dataframe"""
        try:
            # df = self.get_data()
            df = dat.copy()
            if not df.empty:
                bs, d14, m1, m2, m3, m4, m5, m6, wd = self.reconst(df, write)
                # bs.rename(columns={'bs_interviewer':'lb_interviewer'}, inplace=True)
                # self.geocodes(bs)
                bs['lb_interviewer'] = bs['bs_interviewer']
                wd['lb_interviewer'] = wd['wd_interviewer']
                # wd.rename(columns={'wd_interviewer':'lb_interviewer'}, inplace=True)
                query_report = pd.concat(
                    [self.baseline(bs), self.wealth_index(bs), self.mbfes(bs), self.mbfes(m6), self.phq9(bs),
                     self.phq9(m3), self.phq9(m6), self.lbw_1(d14), self.lbw(m1), self.lbw(m2), self.lbw(m3),
                     self.lbw(m4), self.lbw(m5), self.lbw(m6),
                     self.mobidity1(m1), self.mobidity3(m3), self.mobidity6(m6), self.MDAT(m6), self.wdaw(wd),
                     self.exit(m6)])
                if write:
                    query_report.to_csv("ARL_query_report.csv", index=False)
                return query_report
            else:
                print("Gathered an empty dataset")
                return pd.DataFrame([])
        except Exception as e:
            print("Error returning: {}".format(e))
            return pd.DataFrame([])

    def geoCodes(self, ds):
        dss = ds.loc[(~(ds.infant_id.isin(wd.infant_id.to_list())))].copy()
        dss.bs_facility = dss.bs_facility.replace({1: 'Rabai', 2: 'Mariakani', 3: 'Jibana', 4: 'Kilifi'})
        dss['GPS_status'] = 'Missing'
        dss.loc[(dss.cd_lat.notnull()) & (dss.cd_long.notnull()), 'GPS_status'] = 'Location captured'
        dss.loc[((dss.cd_lat.isna()) & (dss.cd_long.notnull())) | (
                    (dss.cd_lat.notnull()) & (dss.cd_long.isna())), 'GPS_status'] = 'Incomplete data'
        dss.rename(columns={'infant_id': 'Participant_id', 'enrollment_date': 'Baseline_date', 'bs_facility': 'Site',
                            'bs_interviewer': 'RA'}, inplace=True)
        dss.sort_values('Baseline_date', inplace=True)
        return pd.crosstab(dss.Site, dss.GPS_status), dss[dss.GPS_status != 'Location captured'][
            ['Participant_id', 'Baseline_date', 'Site', 'GPS_status', 'RA']]

    def style_df(self, ds):
        table = ds.style.set_table_styles([{'selector': '',
                                            'props': [('border',
                                                       '2px solid green')]},
                                           {'selector': 'th', 'props': [('border', '2px solid green')]},
                                           {'selector': 'td', 'props': [('border', '1px solid blue')]}
                                           ])
        return table

ac = ArlModel()
#ar = Arl()
df = ac.get_data() # API data import from REDCap, requires an export API.
#data = pd.read_csv('ARLData_June-08-2025.csv')
ds_backup = df.copy() # Disabled for now, usage for daily backup
ds=ac.const_arl(df)
#|-------------------------------------------------------------------------------|
file = f"C:/Users/george.obanda/OneDrive - Aga Khan University/AKU/ARL/Data/Participant_Followup_Data/Participant_Followup_Data"
file2 = f"C:/Users/george.obanda/OneDrive - Aga Khan University/AKU/ARL/Data/ARLData/ARLData_{datetime.now().strftime('%B-%d-%Y')}"
#plst = ds[['redcap_event_name','infant_id','bs_mid','cg_initials','cg_infant_rship','cg_contact','cg_contact_alt','cd_lat','cd_long','cg_infant_rship_other']].copy()
# plst = plst[plst.redcap_event_name=="baseline_arm_1"].copy()
# plst.cg_contact = plst.cg_contact.fillna(0)
# plst.cg_contact = plst.cg_contact.astype(int)
# plst.cg_infant_rship = plst.cg_infant_rship.replace({1.0:'Mother(biological mother)', 2.0:'Father', 3.0:'Grandparents', 4.0:'Brother', 5.0:'Sister', 77.0:'Other'})
# plst.loc[(plst.cg_infant_rship=="Other"), 'cg_infant_rship']=plst['cg_infant_rship_other']
# plst.drop('cg_infant_rship_other', axis=1, inplace=True)
# plst.rename(columns={'infant_id':'Study ID','bs_mid':'Mother ID','cg_initials':'Caregiver initials','cg_infant_rship':'Caregiver relationship','cg_contact':'Contact', 'cg_contact_alt':'Alternative Contact', 'cg_contact_alt':'Alternative Contact',  'cd_lat':'Latitude', 'cd_long':'Longitude'}, inplace=True)
# plst.replace({0:''}, inplace=True)
# plst = plst.drop_duplicates()
# plst.reset_index(drop=True, inplace=True)
#ac.backup_encrypt_df(plst.fillna(''), file) # saves participant information in encrypted formart. Currently disabled, we will generate an encryption_key
ac.backup_encrypt_df(ds_backup.fillna(''), file2) # Data backup everytime this project runs. Currently disabled, we will generate an encryption_key
bs, d1, m1, m2, m3, m4, m5, m6, wd = ac.reconst(df)
#|-------------------------------------------------------------------------------|
bs, d14, m1, m2, m3,m4, m5, m6, wd= ac.reconst(df)
d1 = d14.copy()
#bs - baseline, d1 - Day 14, m1 - Month 1, m2 - Month 2, m3 - Month3, m4 - Month 4, m5 - Month 5, m6 - Month 6, wd - Withdrawal.
#with open("C:/Users/george.obanda/OneDrive - Aga Khan University/AKU/ARL/logs/backup_log.txt", "a") as log:
os.makedirs("logs", exist_ok=True)
with open("logs/backup_log.txt", "a") as log:
    ac.backup_encrypt_df(df)
    log.write(f"[{datetime.now()}] Backup started\n")
    log.write("Backup successful\n")

