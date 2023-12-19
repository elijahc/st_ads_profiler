import numpy as np
import pandas as pd
import matplotlib as mpl
mpl.use("agg")
import streamlit as st
import calmap
import altair as alt

month_names = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun','Jul', 'Aug','Sep','Oct','Nov','Dec']
rotation_names = ['UCH OR', 'VA OR', 'APS-Blk', 'APS-Rnd', 'DH-OR', 'PPS', 'STICU', 'CP']
age_grp_map = {
    'e. >= 65 year':'geriatric',
    'd. >= 12 yr. and < 65 yr.':'adult',
    'c. < 12 Years':'child',
    'b. < 3 Years':'toddler',
    'a. < 3 months':'infant'
    }

st.session_state.ga = []
st.session_state.epidural = []
st.session_state.pnb = []
st.session_state.spinal= []

# Upload XLS data
st.sidebar.markdown("## Upload a caselog")

uploaded_file = st.sidebar.file_uploader(".xls file", type=["xls"])


st.header('**ACGME case log profiler**')
metrics_ph = st.empty()

report,details = st.tabs(['Viz','Tables'])
with report:
    yearplot_ph=st.empty()

with details:
    st.subheader('**Debug**')
    with st.expander("Parsed xls"):
        df_ph = st.empty()

    with st.expander("Processed df"):
        processed_ph = st.empty()


if uploaded_file is not None:
    def load_xls():
        xls_df = pd.read_excel(uploaded_file,skiprows=10)
        df_end = xls_df[-10:]
        last_row = df_end.index[df_end[df_end.columns[-1]].str.startswith('Case Total')==True].tolist()[0]
        last_row = last_row-1
        xls_df = xls_df.iloc[:last_row]
        xls_df = xls_df.dropna(axis=1,how='all').dropna(axis=0,how='all')
        xls_df = xls_df.rename(columns={k:v for k,v in zip(xls_df.columns,['attr','value','area-val'])}).reset_index(drop=True)
        # case_idxs = df.attr=='Case Date:'        
        return xls_df
    
    df = load_xls()
    with df_ph.container():
        st.dataframe(df,hide_index=True)

    def extract_log_meta(df_):
        with processed_ph.container():
            st.write('df')
            st.dataframe(df_)

        df_area = df_[['value','area-val']].iloc[7:]
        df_area = df_area[~df_area.value.isin(['Area', 'Non-Trauma','Unanticipated', 'Trauma Anticipated', 'Trauma'])]
        asa = df_area[df_area['value'].isin(['ASA Physical Status'])]
        # separate pain logs from cases based on ASA presence

        df_dict = df_[['attr','value']].iloc[:7].to_dict()
        df_dict = {k:v for k,v in zip(df_dict['attr'].values(),df_dict['value'].values())}

        with processed_ph.container():
            st.write('df_dict')
            st.dataframe(df_dict)

        if len(asa)>0:
            df_dict['ASA'] = asa['area-val']

            # Add subgroup attributes

            with processed_ph.container():
                st.write('last partial')
                st.json(df_dict)

            return pd.Series(df_dict)
        else:
            return None

    def process_case(grp_id, cdf):
        split_idx = int(list(np.where(cdf['value']=='Area')[0])[0])
        df_dict = cdf[['attr','value']].iloc[:split_idx].to_dict()
        df_dict = {k:v for k,v in zip(df_dict['attr'].values(),df_dict['value'].values())}

        areas = cdf[['value','area-val']].iloc[split_idx+1:].dropna()
        asa = areas[areas['area-val'].str.startswith('ASA')]['area-val']
        if len(asa)==1:
            df_dict['ASA']=asa.values[0]
        else:
            df_dict['ASA']=None
            
        if areas['area-val'].str.startswith('General').any():
            st.session_state.ga.append(int(grp_id))

        if areas['area-val'].str.startswith('Epidural').any():
            st.session_state.epidural.append(int(grp_id))

        if areas['area-val'].str.startswith('Peripheral Nerve Block').any():
            st.session_state.pnb.append(int(grp_id))

        if areas['area-val'].str.startswith('Spinal').any():
            st.session_state.spinal.append(int(grp_id))

        return df_dict

    def process_xls(df):
        case_idxs = df.attr=='Case Date:'
        case_grper = case_idxs.astype(int).cumsum()
        grp_iter = df.groupby(case_grper)
        dat_accum = []
        for idx,sdf in grp_iter:
            res = process_case(idx,sdf)
            dat_accum.append(res)
            
        # log_meta = .apply(extract_log_meta).reset_index(drop=True)
        # if 'Patient Age:' in log_meta.keys():
        #     log_meta['age_grp']=log_meta['Patient Age:'].replace(age_grp_map)

        processed = pd.DataFrame(dat_accum)
        if 'Patient Age:' in processed.columns.values:
            processed['age_grp']=processed['Patient Age:'].replace(age_grp_map)
        return processed
    

    lm = process_xls(df)
    with processed_ph.container():
        st.dataframe(lm)

    with st.sidebar.header('2. Customize plot'):
        # for yr in sorted(lm.year.unique()):
        #     st.sidebar.text_input(
        #         '{} xaxis labels'.format(yr),
        #         value=','.join(month_names),
        #         )
        pass

    def plot_log(log_meta, date_col='Case Date:',cust_xlabs=None):
        log_meta['year'] = log_meta['Case Date:'].dt.year
        log_meta['month'] = log_meta['Case Date:'].dt.month
        log_meta['day_name'] = log_meta['Case Date:'].dt.day_name()
        
        log_meta_agg = log_meta.groupby(['Case Date:','Case Year:','Site:']).count()['year'].reset_index().rename(columns={'year':'count'})
        log_meta_agg['offset_date'] = log_meta_agg['Case Date:']-pd.Timedelta(546-365, 'd')

        fig,axs = calmap.calendarplot(
            log_meta_agg.set_index(date_col)['count'],
            cmap='YlGn',
            fillcolor='lightgrey',
            linewidth=2,
            # fig_kws={'figsize':(8,6)},
            daylabels=list('MTWTFSS'),
            dayticks=[0, 2, 4, 6],
            monthly_border=True,
        );

        if date_col == 'offset_date':
            xlabs = ['Jul','Aug','Sep','Oct','Nov','Dec','Jan','Feb','Mar','Apr','May','Jun']
            for ax in axs:
                ax.set_xticklabels(xlabs);
        
        return fig,axs


    with yearplot_ph.container():
        try:
            f,axs = plot_log(lm)
            st.pyplot(f,use_container_width=True)
        except:
            st.write('Internal Error')

    with details:
        with st.expander('GA'):
            st.session_state.ga = lm[lm.index.isin(st.session_state.ga)].reset_index(drop=True)
            st.dataframe(st.session_state.ga)

        with st.expander('Epidural'):
            st.session_state.epidural = lm[lm.index.isin(st.session_state.epidural)].reset_index(drop=True)
            st.dataframe(st.session_state.epidural)

        with st.expander('PNB'):
            st.session_state.pnb = lm[lm.index.isin(st.session_state.pnb)].reset_index(drop=True)
            st.dataframe(st.session_state.pnb)

        with st.expander('Spinal'):
            st.session_state.spinal = lm[lm.index.isin(st.session_state.spinal)].reset_index(drop=True)
            st.dataframe(st.session_state.spinal)

    with metrics_ph.container():
        c1,c2,c3,c4 = st.columns(4)
        c1.metric('GA',len(st.session_state.ga))
        c2.metric('Epidural (40)', len(st.session_state.epidural))
        c3.metric('Nerve Block (40)', len(st.session_state.pnb))
        c4.metric('Spinal (40)', len(st.session_state.spinal))

st.sidebar.markdown("""
    > *[How to get ACGME caselog](https://www.loom.com/share/9bc9d25c013b489abec09eb086bff1c9?sid=27f43eeb-4f16-4565-9cd4-c16a548ad252)*

    > [Example XLS input file](https://github.com/elijahc/st_ads_profiler/raw/master/ref/ACLResProcDetail-edc-sample.xls)
""") 
