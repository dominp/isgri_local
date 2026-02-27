#!/bin/sh
#PBS -q iasf
#PBS -l nodes=compute-0-TEMPLATE_NODE
#PBS -J 1-TEMPLATE_MAXNO
#PBS -e ABSPATH/log/error/
#PBS -o ABSPATH/log/output/
##### Variables ---- Set number of ScW in line 5
SCWLIST=ABSPATH/scw/TEMPLATE_SCW
OUTPUT=TEMPLATE_OUTPUT
SPECAT=ABSPATH/specat/TEMPLATE_SPECAT

E_MIN="18"
E_MAX="250"

##### Config environment #####
id=$(sed "${PBS_ARRAY_INDEX}q;d" $SCWLIST)
source /share/apps/mario/setup/hesw.werewolf.bashrc
osainit


export REP_BASE_PROD=TEMPLATE_OSA_RBP
export PFILES="${REP_BASE_PROD}/obs/${id}/pfiles;${ISDC_ENV}/pfiles:$HEADAS/syspfiles"
export ISDC_REF_CAT=${REP_BASE_PROD}/cat/hec/gnrl_refr_cat_0043.fits
export COMMONSCRIPT=1

#####
mkdir -p ${REP_BASE_PROD}/obs/${id}/pfiles
mkdir -p ${REP_BASE_PROD}/ids
echo $id > ${REP_BASE_PROD}/ids/"${id}.lst"
#####

cd ${REP_BASE_PROD}
og_create idxSwg="ids/${id}.lst" ogid="$id" baseDir="./" instrument=IBIS
rm ${REP_BASE_PROD}/ids/"${id}.lst"
cd ${REP_BASE_PROD}/obs/$id
cp $SPECAT specat.fits
chmod -w specat.fits
######

IC_DIR="${REP_BASE_PROD}/ic"

ibis_science_analysis ogDOL="./og_ibis.fits" startLevel=COR endLevel=DEAD SCW1_GTI_gtiUserI=""

ii_pif inOG="" outOG="og_ibis.fits" inCat=specat.fits \
                num_band=1 E_band_min=${E_MIN} E_band_max=${E_MAX} \
        mask="${IC_DIR}/ibis/mod/isgr_mask_mod_0003.fits"\
        tungAtt="${IC_DIR}/ibis/mod/isgr_attn_mod_0010.fits" \
        aluAtt="${IC_DIR}/ibis/mod/isgr_attn_mod_0011.fits" \
        leadAtt="${IC_DIR}/ibis/mod/isgr_attn_mod_0012.fits"


mkdir -p $OUTPUT/${id:0:4}
cp $REP_BASE_PROD/obs/$id/scw/*/isgri_model.fits $OUTPUT/${id:0:4}/${id}_isgri_model.fits
gzip -f $OUTPUT/${id:0:4}/${id}_isgri_model.fits
rm -R $REP_BASE_PROD/obs/$id