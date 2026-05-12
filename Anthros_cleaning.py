import pandas as pd
from cryptography.fernet import Fernet
from redcap import Project
from dateutil.relativedelta import relativedelta
from datetime import date
import re

class Anthros:
    # Set up thresholds and rules for each anthropometric variable
    thresholds = {
        'weight': {'col': 'lb_weight_final', 'daily_limit': 35, 'allow_decrease': True},  # 30g/day for weight, decrease allowed
        'length': {'col': 'lb_length_final', 'daily_limit': 0.1, 'allow_decrease': False}, # 0.1cm/day for length, no decrease allowed
        'muac': {'col': 'lb_muac_final', 'daily_limit': None, 'allow_decrease': True},     # MUAC has special rules, no limit
        'hc': {'col': 'lb_head_circum_final', 'daily_limit': 2, 'allow_decrease': False}   # 2mm/day for head circumference
    }
    # Map numerical codes for interviewers to their initials
    interviewer_map = {1: 'LAM', 2: 'MB', 3: 'MMK', 4: 'SRK'}

    # Map event names from REDCap to readable visit names
    event_map = {'baseline_arm_1': 'baseline', 'day_14_arm_1': 'day14', '1st_month_arm_1': 'month1', '2nd_month_arm_1': 'month2',
                 '3rd_month_arm_1': 'month3', '4th_month_arm_1': 'month4', '5th_month_arm_1': 'month5', '6th_month_arm_1': 'month6'}

    # Define the correct chronological order of visits
    visit_order = ['baseline', 'day14', 'month1', 'month2', 'month3', 'month4', 'month5', 'month6']
    # Visit order used for sorting including birth and discharge
    visit_order2 = ['birth', 'discharge', 'day14', 'month1', 'month2', 'month3', 'month4', 'month5', 'month6']

    def decrypt_key(self, k1, k2):
        fd = "C:/Users/george.obanda/OneDrive - Aga Khan University/AKU/ARL/yek/"
        key = open(f"{fd}{k1}.key", "rb").read()
        cipher_suite = Fernet(key)
        with open("{0}{1}.txt".format(fd, k2), "rb") as f:
            encrypted_key = f.read()
        decrypted_key = cipher_suite.decrypt(encrypted_key).decode()
        return decrypted_key
    def get_data(self):
        """Gathers data from redcap server
        """
        try:
            url = 'https://redcap.ea.aku.edu:8088/redcap/redcap_v13.10.0/api/'
            key = self.decrypt_key("kepart2", "adtp_a")
            index = 'infant_id'
            arl = Project(url, key)
            data = arl.export_records(format_type='df', df_kwargs={'index_col': index})
            print("Gathered data successfully")
            data = data.reset_index()
            for col in [c for c in data.columns if '_mid' in c]:
                data[col] = data['infant_id'].str.split('-').str[0]
            return data
        except Exception as e:
            print("Error gathering data returning: {}".format(e))
            return pd.DataFrame([])

    def implausible_anthros(self, df, outputfile=None):
        baseline = df[df['redcap_event_name'] == 'baseline_arm_1'].copy()
        baseline['infant_dob'] = pd.to_datetime(baseline['infant_dob'], errors='coerce')
        baseline['mt_dsc_date'] = pd.to_datetime(baseline['mt_dsc_date'], errors='coerce')

        # ---------------- Birth visit ----------------
        birth = baseline[
            ['infant_id', 'infant_dob',
             'bth_weight_final', 'bth_length_final',
             'bth_head_circum_final', 'bs_interviewer']
        ].copy()

        birth.rename(columns={
            'infant_dob': 'visit_date',
            'bth_weight_final': 'weight',
            'bth_length_final': 'length',
            'bth_head_circum_final': 'head_circum'
        }, inplace=True)

        birth['muac'] = pd.NA
        birth['visit'] = 'birth'
        birth['RA_Initial'] = birth['bs_interviewer'].map(self.interviewer_map)
        birth = birth[['infant_id', 'visit', 'visit_date',
                       'weight', 'length', 'muac', 'head_circum', 'RA_Initial']]

        # ---------------- Discharge visit ----------------
        discharge = baseline[
            ['infant_id', 'mt_dsc_date',
             'dsc_weight_final', 'dsc_length_final',
             'dsc_muac_final', 'dsc_head_circum_final', 'bs_interviewer']
        ].copy()

        discharge.rename(columns={
            'mt_dsc_date': 'visit_date',
            'dsc_weight_final': 'weight',
            'dsc_length_final': 'length',
            'dsc_muac_final': 'muac',
            'dsc_head_circum_final': 'head_circum'
        }, inplace=True)

        discharge['visit'] = 'discharge'
        discharge['RA_Initial'] = discharge['bs_interviewer'].map(self.interviewer_map)
        discharge = discharge[['infant_id', 'visit', 'visit_date','weight', 'length', 'muac', 'head_circum', 'RA_Initial']]

        # ---------------- Follow-up visits ----------------
        followup = df[df['redcap_event_name'].isin(self.event_map)].copy()
        followup['visit'] = followup['redcap_event_name'].map(self.event_map)
        followup['visit_date'] = pd.to_datetime(followup['lb_visit_date'], errors='coerce')

        followup = followup[
            ['infant_id', 'visit_date', 'visit',
             'lb_weight_final', 'lb_length_final',
             'lb_muac_final', 'lb_head_circum_final',
             'lb_interviewer']
        ].copy()

        followup.rename(columns={
            'lb_weight_final': 'weight',
            'lb_length_final': 'length',
            'lb_muac_final': 'muac',
            'lb_head_circum_final': 'head_circum'
        }, inplace=True)

        followup['RA_Initial'] = followup['lb_interviewer'].map(self.interviewer_map)
        followup = followup[['infant_id', 'visit', 'visit_date',
                             'weight', 'length', 'muac', 'head_circum', 'RA_Initial']]

        # ---------------- Combine all visits ----------------
        frames = [birth, discharge, followup]
        frames = [f for f in frames if not f.empty]

        combined = pd.concat(frames, ignore_index=True)
        combined = combined.dropna(
            subset=['weight', 'length', 'muac', 'head_circum'],
            how='all'
        )

        combined['visit'] = pd.Categorical(
            combined['visit'],
            categories=self.visit_order2,
            ordered=True
        )

        combined.sort_values(['infant_id', 'visit'], inplace=True)
        combined.reset_index(drop=True, inplace=True)

        # Keep visit_date as datetime for calculations
        combined['visit_date'] = pd.to_datetime(combined['visit_date'], errors='coerce')

        # ---------------- Flagging decreases ----------------
        flags = []
        weight_diffs, length_diffs, muac_diffs, hc_diffs = {}, {}, {}, {}

        for infant_id, group in combined.groupby('infant_id'):

            group = group.sort_values('visit')

            prev_weight = prev_length = prev_muac = prev_hc = None
            prev_visit = None
            prev_date = None

            for idx, row in group.iterrows():

                curr_weight = row['weight']
                curr_length = row['length']
                curr_muac = row['muac']
                curr_hc = row['head_circum']
                curr_visit = row['visit']
                curr_date = row['visit_date']
                curr_RA = row.get('RA_Initial', pd.NA)

                weight_diff = round(curr_weight - prev_weight, 2) if pd.notna(curr_weight) and pd.notna(
                    prev_weight) else pd.NA
                length_diff = round(curr_length - prev_length, 2) if pd.notna(curr_length) and pd.notna(
                    prev_length) else pd.NA
                muac_diff = round(curr_muac - prev_muac, 2) if pd.notna(curr_muac) and pd.notna(prev_muac) else pd.NA
                hc_diff = round(curr_hc - prev_hc, 2) if pd.notna(curr_hc) and pd.notna(prev_hc) else pd.NA

                weight_diffs[idx] = weight_diff
                length_diffs[idx] = length_diff
                muac_diffs[idx] = muac_diff
                hc_diffs[idx] = hc_diff

                # -------- LENGTH DECREASE --------
                if pd.notna(length_diff) and length_diff < -0.5:
                    flags.append({
                        'infant_id': infant_id,
                        'from_visit': prev_visit,
                        'to_visit': curr_visit,
                        'visit_date': curr_date,  # ← IMPORTANT FIX
                        'measurement': 'length',
                        'from_value': round(prev_length, 2),
                        'to_value': round(curr_length, 2),
                        'difference': round(length_diff, 2),
                        'message': f'length reduced by {round(length_diff, 2)} cm',
                        'RA_Initial': curr_RA
                    })

                # -------- HC DECREASE --------
                if pd.notna(hc_diff) and hc_diff < -0.5:
                    flags.append({
                        'infant_id': infant_id,
                        'from_visit': prev_visit,
                        'to_visit': curr_visit,
                        'visit_date': curr_date,  # ← IMPORTANT FIX
                        'measurement': 'head_circum',
                        'from_value': round(prev_hc, 2),
                        'to_value': round(curr_hc, 2),
                        'difference': round(hc_diff, 2),
                        'message': f'head_circum reduced by {round(hc_diff, 2)} cm',
                        'RA_Initial': curr_RA
                    })

                prev_weight = curr_weight
                prev_length = curr_length
                prev_muac = curr_muac
                prev_hc = curr_hc
                prev_visit = curr_visit
                prev_date = curr_date

        # ---------------- Add diff columns ----------------
        combined['weight_diff'] = combined.index.map(weight_diffs)
        combined['length_diff'] = combined.index.map(length_diffs)
        combined['muac_diff'] = combined.index.map(muac_diffs)
        combined['hc_diff'] = combined.index.map(hc_diffs)

        # ---------------- Add diff columns ----------------
        combined['weight_diff'] = combined.index.map(weight_diffs)
        combined['length_diff'] = combined.index.map(length_diffs)
        combined['muac_diff'] = combined.index.map(muac_diffs)
        combined['hc_diff'] = combined.index.map(hc_diffs)

        # ---------------- Rename diff columns ----------------
        combined = combined.rename(columns={
            'weight_diff': 'weight_trend',
            'length_diff': 'length_trend',
            'muac_diff': 'muac_trend',
            'hc_diff': 'hc_trend'
        })

        # ---------------- Reorder so trend follows measurement ----------------
        pairs = [
            ('weight', 'weight_trend'),
            ('length', 'length_trend'),
            ('muac', 'muac_trend'),
            ('head_circum', 'hc_trend')
        ]

        new_order = []
        for col in combined.columns:
            new_order.append(col)
            for m, t in pairs:
                if col == m and t in combined.columns:
                    new_order.append(t)

        seen = set()
        new_order = [x for x in new_order if not (x in seen or seen.add(x))]

        combined = combined[new_order]
        # ---------------- Format visit_date for display ----------------
        combined['visit_date'] = combined['visit_date'].dt.strftime('%d-%m-%y')

        flagged_df = pd.DataFrame(flags)

        if outputfile:
            combined.to_csv(outputfile, index=False)

        return combined, flagged_df

    def validate_growth(self, df):
        # Map REDCap event names to friendly visit names
        df = df.copy()
        df['visit'] = df['redcap_event_name'].map(self.event_map)
        df = df[df['visit'].notnull()].copy()

        # Order visits chronologically
        df['visit'] = pd.Categorical(
            df['visit'],
            categories=self.visit_order,
            ordered=True
        )
        df.sort_values(['infant_id', 'visit'], inplace=True)

        # Convert interviewer codes to initials
        df['lb_interviewer'] = df['lb_interviewer'].map(
            self.interviewer_map
        ).fillna(df['lb_interviewer'])

        # Standardize date formats (KEEP AS DATETIME — not .date)
        df['lb_visit_date'] = pd.to_datetime(df['lb_visit_date'], errors='coerce')
        df['infant_dob'] = pd.to_datetime(df['infant_dob'], errors='coerce')
        df['infant_dob'] = df.groupby('infant_id')['infant_dob'].ffill().bfill()

        results = []

        for var, meta in self.thresholds.items():

            col = meta['col']

            for infant_id, group in df.groupby('infant_id'):

                group = group.sort_values('visit').reset_index(drop=True)
                last_seen = None

                for _, row in group.iterrows():

                    curr_val = row[col]
                    curr_date = row['lb_visit_date']

                    if pd.isnull(curr_val):
                        continue

                    if var == 'muac':
                        continue  # Skip MUAC growth checks

                    if last_seen is not None:

                        prev_val = last_seen[col]
                        prev_date = last_seen['lb_visit_date']
                        prev_visit = last_seen['visit']

                        if pd.notnull(prev_val) and pd.notnull(prev_date) and pd.notnull(curr_date):

                            days_between = (curr_date - prev_date).days

                            if days_between > 0:

                                change = curr_val - prev_val
                                monthly_growth = (change / days_between) * 30
                                flag = None

                                # Age in months at midpoint
                                dob = row['infant_dob']
                                if pd.notnull(dob):
                                    mid_date = prev_date + (curr_date - prev_date) / 2
                                    delta = relativedelta(mid_date, dob)
                                    age_months = round(
                                        delta.years * 12 +
                                        delta.months +
                                        (delta.days / 30.44), 1
                                    )
                                else:
                                    age_months = None

                                # Threshold checks
                                if var == 'weight' and change > 700:
                                    flag = f"Weight gain > 700gms in {days_between} days"

                                #elif var == 'length' and monthly_growth > 3:
                                elif var == 'length' and change> 2.5:
                                    flag = f"Length gain > 2.5cm in {days_between} days"

                                elif var == 'hc' and age_months is not None:

                                    if age_months <= 3 and change > 2:
                                        flag = f"HC gain > 2cm in {days_between} days"

                                    elif 3 < age_months <= 6 and change > 1:
                                        flag = f"HC gain > 1.5cm {days_between} days"

                                if flag:
                                    results.append({
                                        'infant_id': infant_id,
                                        'Visit From': prev_visit,
                                        'Visit To': row['visit'],
                                        'Visit Date': curr_date,  # ← CRITICAL FIX
                                        'Age (Months)': age_months,
                                        'days_between': days_between,
                                        'Prev Value': round(prev_val, 2),
                                        'Curr Value': round(curr_val, 2),
                                        'Change': round(change, 2),
                                        'Monthly growth': round(monthly_growth, 2),
                                        'RA_Initial': row['lb_interviewer'],
                                        'Message': flag,
                                        'variable': var
                                    })

                    last_seen = row

        return pd.DataFrame(results)

    def detect_repeated_anthro_values(self, df):
        # Map event names to simplified visit labels
        df['visit'] = df['redcap_event_name'].map(self.event_map)
        df = df[df['visit'].notnull()].copy()
        df['visit'] = pd.Categorical(df['visit'], categories=self.visit_order, ordered=True)
        df.sort_values(['infant_id', 'visit'], inplace=True)
        df['lb_interviewer'] = df['lb_interviewer'].map(self.interviewer_map).fillna(df['lb_interviewer'])

        variables = {
            'weight': 'lb_weight_final',
            'length': 'lb_length_final',
            'muac': 'lb_muac_final',
            'hc': 'lb_head_circum_final'
        }

        results = []

        for infant_id, group in df.groupby('infant_id'):
            group = group.sort_values('visit').reset_index(drop=True)
            for var_name, col in variables.items():
                consecutive_count = 1
                prev_value = None
                repeated_visits = []

                for i, row in group.iterrows():
                    curr_value = row[col]
                    visit = row['visit']

                    if pd.notnull(curr_value) and curr_value == prev_value:
                        consecutive_count += 1
                        repeated_visits.append(visit)
                    else:
                        if consecutive_count >= 3:
                            results.append({
                                'infant_id': infant_id,
                                'variable': var_name,
                                'current_value': round(prev_value, 2) if isinstance(prev_value, float) else prev_value,
                                'visits': ", ".join(repeated_visits),
                                'RA Initial': row.get('lb_interviewer', None),
                                'Error Message': "Repeated value across 3+ visits"
                            })
                        consecutive_count = 1
                        repeated_visits = [visit] if pd.notnull(curr_value) else []
                        prev_value = curr_value

                # Check at the end of the group
                if consecutive_count >= 3:
                    results.append({
                        'infant_id': infant_id,
                        'variable': var_name,
                        'current_value': round(prev_value, 2) if isinstance(prev_value, float) else prev_value,
                        'visits': ", ".join(repeated_visits),
                        'RA Initial': row.get('lb_interviewer', None),
                        'Error Message': "Repeated value across 3+ visits"
                    })

        return pd.DataFrame(results)
        #Visit Monitoring

    def generate_visit_monitoring(self, data):

        today = pd.to_datetime(date.today())

        facility_map = {
            1: "Rabai",
            2: "Mariakani",
            3: "Jibana",
            4: "Kilifi"
        }

        # ---------------- BASELINE RECORDS ----------------
        baseline = data[
            data['redcap_event_name'] == 'baseline_arm_1'
            ].copy()

        if baseline.empty:
            return {}

        # ---------------- GET WITHDRAWN IDS ----------------
        withdrew_ids = data.loc[
            data['redcap_event_name'] == 'withdrawal_arm_1',
            'infant_id'
        ].unique()

        # ---------------- DATE CLEANING ----------------
        baseline['infant_dob'] = pd.to_datetime(baseline['infant_dob'], errors='coerce')
        baseline['mt_dsc_date'] = pd.to_datetime(baseline['mt_dsc_date'], errors='coerce')
        baseline['enrollment_date'] = pd.to_datetime(baseline['enrollment_date'], errors='coerce')

        baseline['Site'] = baseline['bs_facility'].map(facility_map)

        baseline['year'] = (
            baseline['enrollment_date']
            .dt.year
            .astype("Int64")
            .astype(str)
        )

        # ---------------- AGE CALCULATIONS ----------------
        def format_age(days):
            if pd.isna(days):
                return ""
            months = days // 30
            remaining = days % 30
            return f"{months} m, {remaining} days"

        baseline['Chronological Age Today'] = (
                today - baseline['infant_dob']
        ).dt.days.apply(format_age)

        baseline['Discharge Age Today'] = (
                today - baseline['enrollment_date']
        ).dt.days.apply(format_age)

        # ---------------- VISIT CONFIGURATION ----------------
        visits = {
            #"day14": {"anchor": "mt_dsc_date", "offset": 14},
            "day14": {"anchor": "enrollment_date", "offset": 14},
            #"month1": {"anchor": "mt_dsc_date", "offset": 28},
            "month1": {"anchor": "enrollment_date", "offset": 28},
            "month2": {"anchor": "infant_dob", "offset": 60},
            "month3": {"anchor": "infant_dob", "offset": 90},
            "month4": {"anchor": "infant_dob", "offset": 120},
            "month5": {"anchor": "infant_dob", "offset": 150},
            "month6": {"anchor": "infant_dob", "offset": 180},
        }

        results = {}

        # ---------------- LOOP THROUGH VISITS ----------------
        for visit_name, config in visits.items():

            ds = baseline.copy()
            anchor = config["anchor"]
            offset = config["offset"]

            ds[f'{visit_name}: Ideal'] = ds[anchor] + pd.Timedelta(days=offset)
            ds[f'{visit_name}: Earliest'] = ds[f'{visit_name}: Ideal'] - pd.Timedelta(days=2)
            ds[f'{visit_name}: Latest'] = ds[f'{visit_name}: Ideal'] + pd.Timedelta(days=2)

            # Who has been seen?
            event_code = [
                k for k, v in self.event_map.items()
                if v == visit_name
            ]

            seen_ids = data.loc[
                (data['redcap_event_name'].isin(event_code)) &
                (
                        data['lb_visit_date'].notna() |
                        data['lb_weight_final'].notna()
                ),
                'infant_id'
            ].unique()

            ds["Status"] = None

            # Seen
            ds.loc[
                ds["infant_id"].isin(seen_ids),
                "Status"
            ] = "Seen"

            # Due logic
            for idx in ds.index:

                if ds.loc[idx, "Status"] is not None:
                    continue

                latest = ds.loc[idx, f'{visit_name}: Latest']
                ideal = ds.loc[idx, f'{visit_name}: Ideal']

                if pd.isna(latest) or pd.isna(ideal):
                    continue

                if today <= latest:

                    days = (ideal - today).days

                    if days > 0:
                        ds.loc[idx, "Status"] = f"Due ({days} days)"
                    elif days == 0:
                        ds.loc[idx, "Status"] = "Due (Today)"
                    else:
                        ds.loc[idx, "Status"] = "Due"

            # Missed
            ds.loc[
                (ds["Status"].isna()) &
                (today > ds[f'{visit_name}: Latest']),
                "Status"
            ] = "Missed"

            # Withdrew override
            ds.loc[
                ds["infant_id"].isin(withdrew_ids),
                "Status"
            ] = "Withdrew"

            # -------------------------------------------------
            # SORT ONLY DUE ROWS (Seen/Missed/Withdrew untouched)
            # -------------------------------------------------
            def extract_due_days(status):
                if isinstance(status, str) and status.startswith("Due"):
                    if "Today" in status:
                        return 0
                    match = re.search(r"\((\d+)", status)
                    if match:
                        return int(match.group(1))
                return None

            ds["due_days"] = ds["Status"].apply(extract_due_days)

            due_df = ds[ds["due_days"].notna()].copy()
            non_due_df = ds[ds["due_days"].isna()].copy()

            due_df = due_df.sort_values("due_days")

            ds = pd.concat([due_df, non_due_df])
            ds.drop(columns=["due_days"], inplace=True)

            # Format date columns
            date_cols = [
                f'{visit_name}: Earliest',
                f'{visit_name}: Ideal',
                f'{visit_name}: Latest',
                'enrollment_date'
            ]

            for col in date_cols:
                ds[col] = ds[col].dt.strftime("%Y-%m-%d")

            final = ds[[
                'infant_id',
                'Site',
                'enrollment_date',
                'Chronological Age Today',
                'Discharge Age Today',
                f'{visit_name}: Earliest',
                f'{visit_name}: Ideal',
                f'{visit_name}: Latest',
                'Status',
                'year'
            ]].copy()

            final.rename(columns={
                'infant_id': 'PTID',
                'enrollment_date': 'Enrollment date'
            }, inplace=True)

            results[visit_name] = final

        return results

    def generate_comments_report(self, df):

        df = df.copy()

        # ---------------- MAP VISITS ----------------
        df['visit'] = df['redcap_event_name'].map(self.event_map)

        # Keep only relevant visits
        df = df[df['visit'].notna()].copy()

        # ---------------- CREATE VISIT DATE ----------------
        # Follow-up uses lb_visit_date, baseline falls back to enrollment_date
        df['visit_date'] = pd.to_datetime(df['lb_visit_date'], errors='coerce')
        df['enrollment_date'] = pd.to_datetime(df.get('enrollment_date'), errors='coerce')

        df['visit_date'] = df['visit_date'].fillna(df['enrollment_date'])

        # ---------------- EXTRACT YEAR ----------------
        df['year'] = df['visit_date'].dt.year.astype('Int64')

        # ---------------- KEEP COMMENTS ----------------
        comments_df = df[[
            'infant_id',
            'visit',
            'lb_comment',
            'bs_comment',
            'year'
        ]].copy()

        # ---------------- COMBINE COMMENTS ----------------
        comments_df['combined_comment'] = (
            comments_df[['lb_comment', 'bs_comment']]
            .fillna('')
            .agg(' | '.join, axis=1)
            .str.strip(' |')
        )

        # Remove empty rows
        comments_df = comments_df[
            comments_df['combined_comment'].notna() &
            (comments_df['combined_comment'] != '')
            ]

        # ---------------- PIVOT (WITH YEAR) ----------------
        pivot_df = comments_df.pivot_table(
            index=['infant_id', 'year'],
            columns='visit',
            values='combined_comment',
            aggfunc=lambda x: ' | '.join(filter(None, x))
        ).reset_index()

        # ---------------- ORDER COLUMNS ----------------
        visit_order = [
            'baseline', 'day14', 'month1', 'month2',
            'month3', 'month4', 'month5', 'month6'
        ]

        cols = ['infant_id', 'year'] + [v for v in visit_order if v in pivot_df.columns]
        pivot_df = pivot_df[cols]

        return pivot_df

    def generate_html_report(self, df1, df2, reshaped_df, data, output_path, comments_df=None, query_df=None):
    #def generate_html_report(self, df1, df2, reshaped_df, data, output_path, comments_df=None):
        def format_numeric(df):

            df = df.copy()

            cols_to_format = [
                "length",
                "muac",
                "head_circum",
                "length_trend",
                "muac_trend",
                "hc_trend",
                "Prev Value",
                "Curr Value",
                "Change",
                "Monthly growth",
                "Age (Months)",
                "from_value",
                "to_value",
                "difference"
            ]

            for col in cols_to_format:
                if col in df.columns:
                    df[col] = df[col].apply(
                        lambda x: f"{x:.1f}" if pd.notnull(x) else x
                    )
            cols_to_format2 = ["weight", "weight_trend"]
            for col in cols_to_format2:
                if col in df.columns:
                    df[col] = df[col].apply(
                        lambda x: f"{x:.0f}" if pd.notnull(x) else x
                    )
            return df
        # -------------------------------------------------
        # Helper: add row totals
        # -------------------------------------------------
        def add_totals(df):
            df = df.copy()
            df["Total"] = df.sum(axis=1)
            total_row = df.sum().to_frame().T
            total_row.index = ["Grand Total"]
            return pd.concat([df, total_row])

        # -------------------------------------------------
        # Unpack reshaped + flagged data
        # -------------------------------------------------
        if isinstance(reshaped_df, tuple):
            reshaped_df, flagged_df = reshaped_df
        else:
            flagged_df = pd.DataFrame()

        # -------------------------------------------------
        # YEAR EXTRACTION (FIXED)
        # -------------------------------------------------
        if isinstance(reshaped_df, pd.DataFrame) and not reshaped_df.empty:
            reshaped_df["year"] = pd.to_datetime(
                reshaped_df["visit_date"],
                format="%d-%m-%y",
                errors="coerce"
            ).dt.year

        if not flagged_df.empty and "visit_date" in flagged_df.columns:
            flagged_df["year"] = pd.to_datetime(
                flagged_df["visit_date"],
                errors="coerce"
            ).dt.year
            flagged_df["visit_date"] = pd.to_datetime(flagged_df["visit_date"]).dt.strftime("%Y-%m-%d")
        if not df2.empty and "Visit Date" in df2.columns:
            df2["year"] = pd.to_datetime(
                df2["Visit Date"],
                errors="coerce"
            ).dt.year
            df2["Visit Date"] = pd.to_datetime(
                df2["Visit Date"],
                errors="coerce"
            ).dt.strftime("%Y-%m-%d")
        if not df1.empty and "visit_date" in df1.columns:
            df1["year"] = pd.to_datetime(
                df1["visit_date"],
                errors="coerce"
            ).dt.year

        for df in [reshaped_df, flagged_df, df2, df1]:
            if isinstance(df, pd.DataFrame) and "year" in df.columns:
                df["year"] = df["year"].astype("Int64").astype(str)

        # -------------------------------------------------
        # Color mapping
        # -------------------------------------------------
        pastel_colors = ["#E3EEF9", "#F9EDE3", "#EAF6EA", "#F4E9F9"]

        all_ids = pd.concat([
            df1.get("infant_id", pd.Series(dtype=str)),
            df2.get("infant_id", pd.Series(dtype=str)),
            flagged_df.get("infant_id", pd.Series(dtype=str)),
            reshaped_df.get("infant_id", pd.Series(dtype=str))
            if isinstance(reshaped_df, pd.DataFrame) else pd.Series(dtype=str)
        ]).dropna().unique()

        id_color_map = {
            infant_id: pastel_colors[i % len(pastel_colors)]
            for i, infant_id in enumerate(sorted(all_ids))
        }

        def color_row(row):
            return [
                f"background-color: {id_color_map.get(row.infant_id, '#FFFFFF')}; color: black;"
            ] * len(row)

        # -------------------------------------------------
        # RA LIST
        # -------------------------------------------------
        ra_list = sorted(
            set(df1.get("RA_Initial", pd.Series(dtype=str)).dropna()) |
            set(df2.get("RA_Initial", pd.Series(dtype=str)).dropna()) |
            set(flagged_df.get("RA_Initial", pd.Series(dtype=str)).dropna()) |
            set(reshaped_df.get("RA_Initial", pd.Series(dtype=str)).dropna())
            if isinstance(reshaped_df, pd.DataFrame) else set()
        )

        # -------------------------------------------------
        # Coverage data
        # -------------------------------------------------
        coverage_by_year = self.count_records_by_interviewer_year(data)
        facility_recruitment_by_year = self.count_recruitment_by_facility_year(data)

        # -------------------------------------------------
        # Collect ALL years
        # -------------------------------------------------
        all_years = set()

        for df in [reshaped_df, flagged_df, df2, df1]:
            if isinstance(df, pd.DataFrame) and "year" in df.columns:
                all_years.update(df["year"].dropna().unique())

        all_years.update(str(y) for y in coverage_by_year.keys())
        all_years.update(str(y) for y in facility_recruitment_by_year.keys())

        all_years = sorted(all_years)

        # -------------------------------------------------
        # HTML + JS
        # -------------------------------------------------
        styled_html = """
        <style>

            body { 
                font-family: Arial, sans-serif; 
                margin: 12px; 
            }
        
            h2 { 
                color: #004080; 
                font-size: 20px;
                margin-bottom: 8px;
            }
        
            /* ---------------- MAIN TABS ---------------- */
        
            .tab { 
                display: none; 
            }
        
            .tab-buttons { 
                margin-bottom: 12px; 
            }
        
            .tab-buttons button {
                background-color: #ddd;
                border: none;
                padding: 6px 12px;
                cursor: pointer;
                font-size: 14px;
                margin-right: 4px;
                border-radius: 4px;
            }
        
            .tab-buttons button.active {
                background-color: #004080;
                color: white;
            }
        
            /* ---------------- SUB TABS (Visit Monitoring) ---------------- */
        
            .subtab-buttons {
                margin-bottom: 10px;
                margin-top: 5px;
            }
        
            .subtab-buttons button {
                background-color: #5dade2;
                border: none;
                color: white;
                padding: 5px 10px;
                cursor: pointer;
                font-size: 13px;
                margin-right: 4px;
                border-radius: 4px;
            }
        
            .subtab-buttons button.active {
                background-color: #1f618d;
            }
        
            .subtab {
                display: none;
            }
        
            /* ---------------- TABLE STYLING ---------------- */
        
            table {
                width: 100%;
                border-collapse: collapse;
                margin-bottom: 15px;
                table-layout: auto;        /* allow columns to resize naturally */
                font-size: 12px !important;
            }
        
            table th, 
            table td {
                border: 1px solid #ddd;
                padding: 3px 5px;
                text-align: center;
                font-size: 12px !important;
                white-space: nowrap;
                overflow: hidden;
                text-overflow: ellipsis;
            }
        
            th {
                background-color: #f2f2f2;
                font-weight: 600;
            }
        
            tr:last-child {
                font-weight: bold;
                background-color: #e6f0ff;
            }
        
            select, label {
                font-size: 11px;
            }
        
            /* ---------------- TOOLTIP SUPPORT ---------------- */
        
            td[title] {
                cursor: help;   /* shows help cursor when hovering */
            }
        
            /* ---------------- OPTIONAL: ALLOW ERROR MESSAGE WRAPPING ---------------- */
        
            td:nth-child(12),
            th:nth-child(12) {
                white-space: normal !important;
                max-width: 220px;
                word-wrap: break-word;
            }
            /* Wrap long text in comment columns */
            .comment-cell {
                white-space: normal !important;
                word-wrap: break-word;
                word-break: break-word;
                max-width: 250px;
                text-align: left;
            }
        </style>

        <script>
            /* ==============================
               MAIN TAB CONTROL
            ============================== */
            function openTab(evt, tabName) {
        
                document.querySelectorAll(".tab").forEach(t => 
                    t.style.display = "none"
                );
        
                document.querySelectorAll(".tab-buttons button")
                    .forEach(b => b.classList.remove("active"));
        
                const tab = document.getElementById(tabName);
                if (tab) tab.style.display = "block";
        
                evt.currentTarget.classList.add("active");
            }
            /* ==============================
               SUB TAB CONTROL (Visit Monitoring)
            ============================== */
            function openSubTab(evt, subTabId) {
        
                const container = document.getElementById("visit_monitoring");
                if (!container) return;
        
                container.querySelectorAll(".subtab").forEach(t =>
                    t.style.display = "none"
                );
        
                container.querySelectorAll(".subtab-buttons button")
                    .forEach(b => b.classList.remove("active"));
        
                const subTab = document.getElementById(subTabId);
                if (subTab) subTab.style.display = "block";
        
                evt.currentTarget.classList.add("active");
            }
        
        
            /* ==============================
               YEAR + RA FILTERING
            ============================== */
            function applyFilters() {
        
                const selectedYear = document.getElementById("yearSelect").value;
                const selectedRA = document.getElementById("raSelect").value;
        
                /* -------- YEAR FILTERING -------- */
                document.querySelectorAll("[data-year]").forEach(section => {
        
                    const sectionYear = section.getAttribute("data-year");
        
                    if (selectedYear === "all" || String(sectionYear) === String(selectedYear)) {
                        section.style.display = "block";
                    } else {
                        section.style.display = "none";
                    }
                });
        
                /* -------- RA FILTERING -------- */
                document.querySelectorAll("table").forEach(table => {
        
                    const headers = Array.from(table.querySelectorAll("th"))
                        .map(th => th.innerText.trim());
        
                    /* CASE 1: Tables with RA column */
                    const raIndex = headers.findIndex(h =>
                        h === "RA_Initial" || h === "RA Initial"
                    );
        
                    if (raIndex !== -1) {
        
                        table.querySelectorAll("tbody tr").forEach(row => {
        
                            const cells = row.querySelectorAll("td");
                            if (!cells[raIndex]) return;
        
                            const rowRA = cells[raIndex].innerText.trim();
        
                            if (
                                selectedRA === "all" ||
                                rowRA.toUpperCase().includes(selectedRA.toUpperCase())
                            ) {
                                row.style.display = "";
                            } else {
                                row.style.display = "none";
                            }
                        });
        
                        return;
                    }
        
                    /* CASE 2: Recruitment matrix (columns = RA) */
                    table.querySelectorAll("tr").forEach(row => {
                        row.querySelectorAll("th, td").forEach(cell => {
                            cell.style.display = "";
                        });
                    });
        
                    if (selectedRA === "all") return;
        
                    const selectedIndex = headers.findIndex(h => h === selectedRA);
                    if (selectedIndex === -1) return;
        
                    table.querySelectorAll("tr").forEach(row => {
                        row.querySelectorAll("th, td").forEach((cell, index) => {
                            if (index === 0) return;               // Keep first column
                            if (index === selectedIndex) return;  // Keep selected RA
                            cell.style.display = "none";
                        });
                    });
                });
            }
        
        
            /* ==============================
               PASSWORD PROTECTED ADMIN SECTION
            ============================== */
            function toggleAdminSection() {
        
                const section = document.getElementById("adminSection");
                if (!section) return;
        
                if (section.style.display === "block") {
                    section.style.display = "none";
                    return;
                }
                const password = prompt("Enter admin password:");
                const correctPassword = "ARL@2026";
        
                if (password === correctPassword) {
                    section.style.display = "block";
                } else if (password !== null) {
                    alert("Incorrect password.");
                }
            }        
            /* ==============================
               INITIAL LOAD SETTINGS
            ============================== */
            window.onload = function () {
        
                /* Open first main tab */
                const firstTab = document.querySelector(".tab");
                const firstButton = document.querySelector(".tab-buttons button");
        
                if (firstTab) firstTab.style.display = "block";
                if (firstButton) firstButton.classList.add("active");
        
                /* Hide admin section by default */
                const admin = document.getElementById("adminSection");
                if (admin) admin.style.display = "none";
        
                /* Open default subtab (Summary) */
                const visitTab = document.getElementById("visit_monitoring");
                if (visitTab) {
        
                    const firstSubTab = visitTab.querySelector(".subtab");
                    const firstSubButton = visitTab.querySelector(".subtab-buttons button");
        
                    if (firstSubTab) firstSubTab.style.display = "block";
                    if (firstSubButton) firstSubButton.classList.add("active");
                }
            };
        
         </script>
        """

        # -------------------------------------------------
        # WRITE FILE
        # -------------------------------------------------
        with open(output_path, "w", encoding="utf-8") as f:

            f.write(f"""
            <html>
            <head>
                <title>Anthropometric Data Quality Report</title>
                {styled_html}
            </head>
            <body>

            <h2>ARL Data Quality & Consistency Report</h2>

            <label><strong>Select Year:</strong></label>
            <select id="yearSelect" onchange="applyFilters()">
                <option value="all">All</option>
            """)

            for yr in all_years:
                f.write(f"<option value='{yr}'>{yr}</option>")

            f.write("""
            </select>

            <label style="margin-left:20px;"><strong>Select RA:</strong></label>
            <select id="raSelect" onchange="applyFilters()">
                <option value="all">All</option>
            """)

            for ra in ra_list:
                f.write(f"<option value='{ra}'>{ra}</option>")

            f.write("""
            </select>
            <br><br>

            <div class="tab-buttons">
                <button onclick="openTab(event, 'trend')">Combined Trend</button>
                <button onclick="openTab(event, 'coverage')">Recruitment Status</button>
                <button onclick="openTab(event, 'visit_monitoring')">Visit Monitoring</button>
                <button onclick="openTab(event, 'implausible')">Implausible Decreases</button>
                <button onclick="openTab(event, 'growth')">Unusual Growth</button>
                <button onclick="openTab(event, 'repeats')">Repeated Values</button>
                <button onclick="openTab(event, 'comments')">Comments</button>
                <button onclick="openTab(event, 'form_queries')">Form Queries</button>
            </div>
            """)

            # ---------------- TAB 1 ----------------
            f.write("<div class='tab' id='trend'>")
            if isinstance(reshaped_df, pd.DataFrame) and not reshaped_df.empty:
                for yr in reshaped_df["year"].dropna().unique():
                    df_year = reshaped_df[reshaped_df["year"] == yr]
                    f.write(f"<div data-year='{yr}'>")
                    df_year = format_numeric(df_year)
                    f.write(df_year.style.apply(color_row, axis=1).to_html())
                    f.write("</div>")
            else:
                f.write("<p>No combined anthropometric data available.</p>")
            f.write("</div>")

            # ---------------- TAB 2 ----------------
            f.write("<div class='tab' id='coverage'>")

            # ---------------- RECRUITMENT BY FACILITY ----------------
            f.write("<h4>Recruitment by Facility</h4>")

            for yr, tbl in facility_recruitment_by_year.items():
                tbl = add_totals(tbl)
                f.write(f"<div data-year='{yr}'>")
                f.write(tbl.style.to_html())
                f.write("</div>")

            # ---------------- ADMIN BUTTON ----------------
            f.write("""
            <br>
            <button type="button" onclick="toggleAdminSection()" 
                    style="margin-top:10px; padding:6px 12px; font-size:13px; cursor:pointer;">
                Per RA
            </button>
            """)

            # ---------------- HIDDEN ADMIN SECTION ----------------
            f.write("""
            <div id="adminSection" style="display:none; margin-top:15px;">
                <h4>Number of Recruitment by Visit and Interviewer</h4>
            """)

            for yr, mat in coverage_by_year.items():
                mat = add_totals(mat)
                f.write(f"<div data-year='{yr}'>")
                f.write(mat.style.set_table_attributes('class=\"coverageTable\"').to_html())
                f.write("</div>")

            # Close admin section
            f.write("</div>")

            # Close coverage tab
            f.write("</div>")

            # ---------------- TAB 3 ----------------
            f.write("<div class='tab' id='visit_monitoring'>")

            visit_tables = self.generate_visit_monitoring(data)

            visit_order = ["day14", "month1", "month2", "month3", "month4", "month5", "month6"]

            # =========================================================
            # SUBTAB BUTTONS
            # =========================================================
            f.write("""
            <div class="subtab-buttons">
                <button onclick="openSubTab(event, 'vm_summary')" class="active">Summary</button>
                <button onclick="openSubTab(event, 'vm_day14')">Day 14</button>
                <button onclick="openSubTab(event, 'vm_month1')">Month 1</button>
                <button onclick="openSubTab(event, 'vm_month2')">Month 2</button>
                <button onclick="openSubTab(event, 'vm_month3')">Month 3</button>
                <button onclick="openSubTab(event, 'vm_month4')">Month 4</button>
                <button onclick="openSubTab(event, 'vm_month5')">Month 5</button>
                <button onclick="openSubTab(event, 'vm_month6')">Month 6</button>
            </div>
            """)

            # =========================================================
            # BUILD SUMMARY DATA
            # =========================================================
            summary_rows = []

            summary_rows = []

            # --- count withdrawals ONCE per year ---
            withdrawals = data[data["redcap_event_name"] == "withdrawal_arm_1"]["infant_id"].unique()

            withdrawals_by_year = (
                data[
                    (data["redcap_event_name"] == "baseline_arm_1") &
                    (data["infant_id"].isin(withdrawals))
                    ]
                .assign(year=pd.to_datetime(data["enrollment_date"], errors="coerce").dt.year)
                .groupby("year")["infant_id"]
                .nunique()
            )

            for visit_name in visit_order:

                if visit_name not in visit_tables:
                    continue

                visit_table = visit_tables[visit_name]

                if visit_table.empty or "year" not in visit_table.columns:
                    continue

                for yr in sorted(visit_table["year"].dropna().unique()):
                    df_year = visit_table[visit_table["year"] == yr].copy()
                    df_year["Status"] = df_year["Status"].fillna("")

                    followed_up = (df_year["Status"] == "Seen").sum()
                    missed = (df_year["Status"] == "Missed").sum()

                    # show withdrawal only in first visit row
                    withdrawals = withdrawals_by_year.get(int(yr), 0) if visit_name == "day14" else ""

                    summary_rows.append({
                        "Visit": visit_name,
                        "Followed-Up": int(followed_up),
                        "Missed": int(missed),
                        "Withdrawals": withdrawals,
                        "Year": yr
                    })

            summary_df = pd.DataFrame(summary_rows)

            # =========================================================
            # SUMMARY SUBTAB
            # =========================================================
            f.write("<div class='subtab' id='vm_summary' style='display:block;'>")

            if not summary_df.empty:

                for yr in sorted(summary_df["Year"].unique()):
                    df_sum_year = summary_df[summary_df["Year"] == yr].copy()
                    df_sum_year = df_sum_year.sort_values("Visit")

                    # ---- create totals row (exclude Year) ----
                    totals = {
                        "Visit": "Total",
                        "Followed-Up": df_sum_year["Followed-Up"].sum(),
                        "Missed": df_sum_year["Missed"].sum(),
                        "Withdrawals": df_sum_year["Withdrawals"].replace("", 0).astype(int).sum(),
                        "Year": yr
                    }

                    df_sum_year = pd.concat(
                        [df_sum_year, pd.DataFrame([totals])],
                        ignore_index=True
                    )

                    f.write(f"<div data-year='{yr}'>")
                    f.write(f"<h3>Visit Monitoring Summary {yr}</h3>")
                    f.write(df_sum_year.to_html(index=False))
                    f.write("</div>")

            f.write("</div>")  # END SUMMARY SUBTAB

            # =========================================================
            # VISIT SUBTABS
            # =========================================================
            for visit_name in visit_order:

                if visit_name not in visit_tables:
                    continue

                visit_table = visit_tables[visit_name]

                if visit_table.empty or "year" not in visit_table.columns:
                    continue

                subtab_id = f"vm_{visit_name}"
                f.write(f"<div class='subtab' id='{subtab_id}'>")
                for yr in sorted(visit_table["year"].dropna().unique()):
                    df_year = visit_table[visit_table["year"] == yr].copy()
                    f.write(f"<div data-year='{yr}'>")
                    def color_status(val):
                        if val == "Seen":
                            return "background-color: #28a745; color: white;"
                        elif val == "Missed":
                            return "background-color: orange; color: black;"
                        elif isinstance(val, str) and val.startswith("Due"):
                            return "background-color: #d3d3d3; color: black;"
                        elif val == "Withdrew":
                            return "background-color: #6c757d; color: white;"
                        else:
                            return ""

                    styled = (
                        df_year.style
                        .applymap(color_status, subset=["Status"])
                    )

                    f.write(f"<h4>{visit_name.upper()} Follow-Up</h4>")
                    f.write(styled.to_html(index=False))

                    f.write("</div>")

                f.write("</div>")  # END SUBTAB

            f.write("</div>")  # END VISIT MONITORING TAB

            # ---------------- TAB 4 ----------------
            f.write("<div class='tab' id='implausible'>")
            if not flagged_df.empty:
                for yr in flagged_df["year"].dropna().unique():
                    df_year = flagged_df[flagged_df["year"] == yr]
                    f.write(f"<div data-year='{yr}'>")
                    df_year = format_numeric(df_year)
                    f.write(df_year.style.apply(color_row, axis=1).to_html())
                    f.write("</div>")
            else:
                f.write("<p>No implausible decreases detected.</p>")
            f.write("</div>")

            # ---------------- TAB 5 ----------------
            f.write("<div class='tab' id='growth'>")

            if not df2.empty:

                for yr in sorted(df2["year"].dropna().unique()):

                    df_year = df2[df2["year"] == yr].copy()

                    # format numbers first
                    df_year = format_numeric(df_year)

                    # remove Monthly growth column
                    if "Monthly growth" in df_year.columns:
                        df_year.drop(columns=["Monthly growth"], inplace=True)

                    # rename Change → Growth
                    if "Change" in df_year.columns:
                        df_year.rename(columns={"Change": "Growth"}, inplace=True)

                    f.write(f"<div data-year='{yr}'>")

                    f.write(df_year.style.apply(color_row, axis=1).to_html())

                    f.write("</div>")

            else:
                f.write("<p>No unusual growth patterns detected.</p>")

            f.write("</div>")

            # ---------------- TAB 6 ----------------
            f.write("<div class='tab' id='repeats'>")
            if not df1.empty:
                for yr in df1["year"].dropna().unique():
                    df_year = df1[df1["year"] == yr]
                    f.write(f"<div data-year='{yr}'>")
                    f.write(df_year.style.apply(color_row, axis=1).to_html())
                    f.write("</div>")
            else:
                f.write("<p>No repeated anthropometric values detected.</p>")
            f.write("</div>")

            # ---------------- TAB 7 ----------------
            f.write("<div class='tab' id='comments'>")

            if comments_df is not None and not comments_df.empty:

                df_comments = comments_df.copy()

                # Rename columns for display
                df_comments.rename(columns={
                    'infant_id': 'Study ID',
                    'baseline': 'Baseline',
                    'day14': 'Day 14',
                    'month1': 'Month 1',
                    'month2': 'Month 2',
                    'month3': 'Month 3',
                    'month4': 'Month 4',
                    'month5': 'Month 5',
                    'month6': 'Month 6'
                }, inplace=True)

                visit_cols = [
                    'Baseline', 'Day 14', 'Month 1', 'Month 2',
                    'Month 3', 'Month 4', 'Month 5', 'Month 6'
                ]

                # 🔴 LOOP PER YEAR (enables filtering)
                for yr in sorted(df_comments["year"].dropna().unique()):

                    df_year = df_comments[df_comments["year"] == yr].copy()

                    # Drop year column (used only for filtering)
                    df_year = df_year.drop(columns=['year'])

                    # Clean empty values
                    df_year = df_year.fillna('')

                    # ✅ Apply wrapping to comment columns
                    for col in visit_cols:
                        if col in df_year.columns:
                            df_year[col] = df_year[col].apply(
                                lambda x: f"<div class='comment-cell'>{x}</div>" if x else ""
                            )

                    f.write(f"<div data-year='{int(yr)}'>")
                    f.write(f"<h3>Comments Report {int(yr)}</h3>")

                    # IMPORTANT: escape=False to render HTML
                    f.write(df_year.to_html(index=False, escape=False))

                    f.write("</div>")

            else:
                f.write("<p>No comments available.</p>")

            f.write("</div>")
            # ---------------- TAB 8 ----------------
            f.write("<div class='tab' id='form_queries'>")

            if query_df is not None and not query_df.empty:

                query_df_display = query_df.copy()

                # Rename for display
                query_df_display.rename(columns={
                    "infant_id": "Study ID",
                    "visit": "Visit"
                }, inplace=True)

                # 🔴 LOOP PER YEAR (enables filtering)
                for yr in sorted(query_df_display["year"].dropna().unique()):
                    df_year = query_df_display[
                        query_df_display["year"] == yr
                        ].copy()

                    f.write(f"<div data-year='{yr}'>")
                    f.write(f"<h3>Form Queries {yr}</h3>")
                    f.write(df_year.to_html(index=False))
                    f.write("</div>")

            else:
                f.write("<p>No incomplete or unverified forms found.</p>")

            f.write("</div>")
            f.write("</body></html>")

        print(f"Combined report saved to: {output_path}")
    def anthro_repeat_measurements(self,df):
        suffixes = ("_21", "_22", "_31", "_32")
        filtered_columns = [col for col in df.columns if col.endswith(suffixes)]
        filled_counts = df[filtered_columns].notnull().sum()
        print(filled_counts[filled_counts > 0].sort_values(ascending=False))

    def count_records_by_interviewer_year(self, df):
        """
        Returns By RA split by year.
        Output:
            {
                2025: DataFrame(Event x Interviewer),
                2026: DataFrame(Event x Interviewer)
            }
        """

        df = df.copy()

        # Assign interviewer
        df["RA_Initial"] = pd.NA

        baseline_mask = df["redcap_event_name"] == "baseline_arm_1"
        df.loc[baseline_mask, "RA_Initial"] = (
            df.loc[baseline_mask, "bs_interviewer"]
            .map(self.interviewer_map)
        )

        followup_mask = (
                df["redcap_event_name"].isin(self.event_map.keys()) &
                (df["redcap_event_name"] != "baseline_arm_1")
        )
        df.loc[followup_mask, "RA_Initial"] = (
            df.loc[followup_mask, "lb_interviewer"]
            .map(self.interviewer_map)
        )

        # Map visit labels
        df["Event"] = df["redcap_event_name"].map(self.event_map)
        #df = df[df["RA_Initial"].notna() & df["Event"].notna()]
        df = df[df["Event"].notna()]
        df["RA_Initial"] = df["RA_Initial"].fillna("Unknown")
        # Get visit date (baseline vs follow-up)
        df["visit_date"] = pd.NaT
        df.loc[baseline_mask, "visit_date"] = pd.to_datetime(
            df.loc[baseline_mask, "enrollment_date"], errors="coerce"
        )
        df.loc[followup_mask, "visit_date"] = pd.to_datetime(
            df.loc[followup_mask, "lb_visit_date"], errors="coerce"
        )

        df["year"] = df["visit_date"].dt.year
        df = df[df["year"].isin([2025, 2026])]

        # Order events
        df["Event"] = pd.Categorical(
            df["Event"],
            categories=self.visit_order,
            ordered=True
        )

        coverage_by_year = {}

        for yr in sorted(df["year"].dropna().unique()):
            sub = df[df["year"] == yr]

            matrix = (
                sub.groupby(["Event", "RA_Initial"])
                .size()
                .unstack(fill_value=0)
                .astype(int)
            )
            baseline = data[data["redcap_event_name"] == "baseline_arm_1"].copy()

            baseline["infant_dob"] = pd.to_datetime(baseline["infant_dob"], errors="coerce")
            baseline["enrollment_date"] = pd.to_datetime(baseline["enrollment_date"], errors="coerce")

            baseline["dob_year"] = baseline["infant_dob"].dt.year
            baseline["enroll_year"] = baseline["enrollment_date"].dt.year

            baseline["RA_Initial"] = baseline["bs_interviewer"].map(anth.interviewer_map)

            facility_map = {
                1: "Rabai",
                2: "Mariakani",
                3: "Jibana",
                4: "Kilifi"
            }

            baseline["Facility"] = baseline["bs_facility"].map(facility_map)

            problem = baseline[baseline["dob_year"] != baseline["enroll_year"]]

            print(problem[
                      ["infant_id", "infant_dob", "enrollment_date", "dob_year", "enroll_year", "RA_Initial",
                       "Facility"]
                  ])
            matrix.index.name = "Event"
            coverage_by_year[int(yr)] = matrix

        return coverage_by_year

    def count_records_by_interviewer(self, df):
        """
        Produce Event vs Count tables for each interviewer
        """

        df = df.copy()

        # Assign interviewer
        df["RA_Initial"] = pd.NA

        # Baseline
        baseline_mask = df["redcap_event_name"] == "baseline_arm_1"
        df.loc[baseline_mask, "RA_Initial"] = (
            df.loc[baseline_mask, "bs_interviewer"]
            .map(self.interviewer_map)
        )

        # Follow-ups
        followup_mask = (
                df["redcap_event_name"].isin(self.event_map.keys()) &
                (df["redcap_event_name"] != "baseline_arm_1")
        )
        df.loc[followup_mask, "RA_Initial"] = (
            df.loc[followup_mask, "lb_interviewer"]
            .map(self.interviewer_map)
        )

        # Map visit names
        df["Event"] = df["redcap_event_name"].map(self.event_map)

        # Keep valid rows only
        df = df[df["RA_Initial"].notna() & df["Event"].notna()]

        # Order visits
        df["Event"] = pd.Categorical(
            df["Event"],
            categories=self.visit_order,
            ordered=True
        )

        # Count
        summary = (
            df.groupby(["RA_Initial", "Event"])
            .size()
            .reset_index(name="Counts")
            .sort_values(["RA_Initial", "Event"])
        )

        # Split into separate tables per interviewer
        tables = {
            ra: summary[summary["RA_Initial"] == ra][["Event", "Counts"]]
            .reset_index(drop=True)
            for ra in summary["RA_Initial"].unique()
        }

        return tables

    def count_recruitment_by_facility_year(self, data):
        facility_map = {
            1: "Rabai",
            2: "Mariakani",
            3: "Jibana",
            4: "Kilifi"
        }

        baseline = (
            data.loc[
                data.redcap_event_name == "baseline_arm_1",
                ["infant_id", "bs_facility", "enrollment_date"]
            ]
            .dropna(subset=["bs_facility"])
            .drop_duplicates(subset=["infant_id"])
            .copy()
        )

        baseline["year"] = pd.to_datetime(
            baseline["enrollment_date"],
            errors="coerce"
        ).dt.year

        baseline["Facility"] = baseline["bs_facility"].map(facility_map)

        out = {}
        for yr, dfy in baseline.groupby("year"):
            out[int(yr)] = (
                dfy["Facility"]
                .value_counts()
                .reindex(facility_map.values(), fill_value=0)
                .to_frame("Recruited")
            )
        return out

    def generate_form_completion_queries(self, df, start_date=None, end_date=None):

        df = df.copy()

        # ---------------- DATE HANDLING ----------------
        df["visit_date"] = pd.to_datetime(df["lb_visit_date"], errors="coerce")
        df["enrollment_date"] = pd.to_datetime(df["enrollment_date"], errors="coerce")

        # Fallback for baseline records
        df["visit_date"] = df["visit_date"].fillna(df["enrollment_date"])

        # ---------------- APPLY DATE FILTER ----------------
        if start_date:
            start_date = pd.to_datetime(start_date)
            df = df[df["visit_date"] >= start_date]

        if end_date:
            end_date = pd.to_datetime(end_date)
            df = df[df["visit_date"] <= end_date]

        # ---------------- SITE MAP ----------------
        facility_map = {
            1: "Rabai",
            2: "Mariakani",
            3: "Jibana",
            4: "Kilifi"
        }

        df["Site"] = df["bs_facility"].map(facility_map)

        # ---------------- VISIT MAP ----------------
        df["Visit"] = df["redcap_event_name"].map(self.event_map)
        df["Visit"] = df["Visit"].fillna(df["redcap_event_name"])

        # ---------------- FORMS ----------------
        form_fields = [
            "baseline_form_complete",
            "wealth_index_complete",
            "infant_morbidity_assessment_1_month_complete",
            "infant_morbidity_assessment_3_months_complete",
            "infant_morbidity_assessment_6_months_complete",
            "maternal_nutrition_complete",
            "lbw_follow_up_complete",
            "general_complete",
            "gross_motor_complete",
            "fine_motor_complete",
            "language_complete",
            "social_complete",
            "maternal_breastfeeding_evaluation_scale_complete",
            "maternal_wellbeing_phq9_complete",
            "capture_coordinates_complete",
            "exit_form_complete",
            "withdrawal_complete",
            "sleep_assessment_complete"
        ]

        results = []

        for _, row in df.iterrows():

            for form in form_fields:

                if form in df.columns:

                    status = row[form]

                    if pd.notna(status) and status in [0, 1]:
                        status_label = "Incomplete" if status == 0 else "Unverified"

                        results.append({
                            "infant_id": row["infant_id"],
                            "Site": row["Site"],
                            "visit": row["Visit"],
                            "visit_date": row["visit_date"],
                            "Query": f"{form.replace('_complete', '')} {status_label}"
                        })

        query_df = pd.DataFrame(results)

        # ---------------- ADD YEAR COLUMN (YOUR REQUIREMENT) ----------------
        if not query_df.empty:
            query_df["year"] = (
                query_df["visit_date"]
                .dt.year
                .astype("Int64")
                .astype(str)
            )

        return query_df

#call the class here
#run the anthro cleaning

anth = Anthros()
data = anth.get_data()
result1 = anth.detect_repeated_anthro_values(data)
result2 = anth.validate_growth(data)
result3 = anth.implausible_anthros(data)
query_df = anth.generate_form_completion_queries(data)
output_path = f"C:/Users/george.obanda/OneDrive - Aga Khan University/AKU/ARL/Report/Data_quality_report.html"
visit_monitoring = anth.generate_visit_monitoring(data)
comments_df = anth.generate_comments_report(data)
#anth.generate_html_report(result1,result2,result3,data,output_path,comments_df)
anth.anthro_repeat_measurements(data)

interviewer_tables = anth.count_records_by_interviewer(data)
# for ra, table in interviewer_tables.items():
#     print(f"\nInterviewer – {5re4ra}")
#     print(table.to_str`ing(index=False))
facility_recruitment_by_year = anth.count_recruitment_by_facility_year(data)
#query_df = anth.generate_form_completion_queries(data)
anth.generate_html_report(result1, result2, result3, data, output_path, comments_df, anth.generate_form_completion_queries(data))
