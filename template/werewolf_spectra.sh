#!/bin/sh
#PBS -l nodes=compute-0-TEMPLATE_NODE
#PBS -q iasf
#PBS -J 1-TEMPLATE_MAXNO
#PBS -e ABSPATH/logs/errors/
#PBS -o ABSPATH/logs/output/
##### Variables ---- Set number of ScW in line 5
OUTPUT="ABSPATH/spectra/"
SOURCE="TEMPLATE_SOURCE"
FILE="ABSPATH/data.txt"
SPECAT="ABSPATH/specat.fits"



source /share/apps/mario/setup/hesw.werewolf.bashrc
####

line=$(sed "${PBS_ARRAY_INDEX}q;d" $FILE)
IFS="," read -r swid tstart tend <<< "$line"




# Set up environment
osainit
export REP_BASE_PROD=TEMPLATE_OSA_RBP/
export PFILES="${REP_BASE_PROD}/obs/${swid}_${tstart}_${tend}/pfiles;${ISDC_ENV}/pfiles:$HEADAS/syspfiles"
export ISDC_REF_CAT=${REP_BASE_PROD}/cat/hec/gnrl_refr_cat_0043.fits
export COMMONSCRIPT=1



cd $REP_BASE_PROD

mkdir -p ${REP_BASE_PROD}/obs/${swid}_${tstart}_${tend}/pfiles
mkdir -p ${REP_BASE_PROD}/ids
echo $swid > ${REP_BASE_PROD}/ids/"${swid}_${tstart}_${tend}.lst"

##### 

og_create idxSwg="${REP_BASE_PROD}/ids/${swid}_${tstart}_${tend}.lst" ogid="${swid}_${tstart}_${tend}" baseDir="./" instrument=IBIS
cd $REP_BASE_PROD/obs/${swid}_${tstart}_${tend}
cp $SPECAT specat.fits
#####
gti_user gti.fits group=og_ibis.fits begin="${tstart}" end="${tend}"
chmod -w gti.fits

ibis_science_analysis ogDOL="./og_ibis.fits" startLevel=COR endLevel=SPE CAT_refCat="$ISDC_REF_CAT[ISGRI_FLAG>0]" \
 SCW1_GTI_gtiUserI="gti.fits" SCW2_cat_for_extract="specat.fits" IBIS_nregions_spe=1 IBIS_nbins_spe="-TEMPLATE_BINS" \
 IBIS_energy_boundaries_spe="TEMPLATE_EMIN TEMPLATE_EMAX"

#####

spe_pick group="og_ibis.fits" source=${SOURCE} rootname=${swid}_${tstart}_${tend}
cp ${swid}_${tstart}_${tend}* ${OUTPUT} 
rm -fr ${REP_BASE_PROD}/obs/${swid}_${tstart}_${tend}