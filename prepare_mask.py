import os, shutil
import numpy as np
from astropy.io import fits
from itertools import cycle

template_path = "/zeus1/isgri_local/template/"


def prepare_specat(name, ra, dec, inpath, outpath):
    with fits.open(inpath) as f:
        d = f[1].data
        d["SOURCE_ID"][0] = name
        d["NAME"][0] = name
        d["RA_OBJ"][0] = ra
        d["RA_FIN"][0] = ra
        d["DEC_OBJ"][0] = dec
        d["DEC_FIN"][0] = dec
        f.writeto(outpath, overwrite=True)


def create_scw_file(path, name, scws, maxno=5000):
    noscws = len(scws)
    if noscws > maxno:
        no_arrays = len(scws) // maxno + 1
        scws = np.array_split(scws, no_arrays)
        noscws = len(scws[0])
    else:
        scws = [scws]
    file_names = []
    for i, scws_arr in enumerate(scws):
        scw_file = os.path.join(path, f"{name}{i}.txt")
        file_names.append(os.path.basename(scw_file))
        with open(scw_file, "w") as f:
            for scw in scws_arr:
                if type(scw) != str:
                    scw = scw.decode("UTF-8")
                print(scw, file=f)
    return noscws, file_names


def prepare_masks(
    name,
    scws,
    workdir,
    specat_path=None,
    ra=None,
    dec=None,
    nodes=None,
    output_path=None,
    findgrb=True,
    emin=15,
    emax=300,
):
    workdir = os.path.join(workdir, "Mask")
    if os.path.exists(workdir):
        raise ValueError(f"{workdir} already exists")

    name = name.strip().replace(" ", "_")
    os.makedirs(workdir)
    os.makedirs(os.path.join(workdir, "scw"))
    os.makedirs(os.path.join(workdir, "exec"))
    os.makedirs(os.path.join(workdir, "specat"))
    os.makedirs(os.path.join(workdir, "log"))
    os.makedirs(os.path.join(workdir, "log", "output"))
    os.makedirs(os.path.join(workdir, "log", "error"))

    if specat_path:
        specat_name = os.path.basename(specat_path)
        shutil.copy(specat_path, os.path.join(workdir, "specat", specat_name))
    elif not ra or not dec:
        raise ValueError("RA and DEC must be provided if specat_path is not provided")
    else:
        specat_name = name + ".fits"
        prepare_specat(
            name, ra, dec, os.path.join(template_path, "specat.fits"), os.path.join(workdir, "specat", specat_name)
        )

    scw_name = name + "_"
    no_scws, scw_lists = create_scw_file(os.path.join(workdir, "scw"), scw_name, scws)

    if nodes is None:
        nodes = ["0", "1"]

    if output_path is None:
        output_path = os.path.join("/storage/dominik/SRCS/", name + "/")
    else:
        output_path = os.path.join(output_path, name + "/")
    with open(template_path + "Wmask.sh") as f:
        template = f.read()
    template_keys = {
        "TEMPLATE_MAXNO": no_scws,
        "TEMPLATE_SPECAT": specat_name,
        "TEMPLATE_OUTPUT": output_path,
    }
    for key in template_keys:
        template = template.replace(key, str(template_keys[key]))
    exec_files = []
    for ids, (scw_list, node) in enumerate(zip(scw_lists, cycle(nodes))):
        exec_files.append(file := f"job_{ids}.sh")
        with open(os.path.join(workdir, "exec", file), "w") as f:
            f.write(template.replace("TEMPLATE_SCW", scw_list).replace("TEMPLATE_NODE", node))

    with open(os.path.join(workdir, "exec.sh"), "w") as f:
        print(r"#!/bin/sh", file=f)
        print(rf'mkdir -p "{output_path}"', file=f)
        print(r'DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )" ', file=f)
        for idf, file in enumerate(exec_files):
            print(rf'sed -i "s|ABSPATH|$DIR|g" "exec/{file}"', file=f)
            print(rf"qsub -N {name}_{idf} exec/{file}", file=f)

    if findgrb:
        workdir = workdir[:-4]
        prepare_findgrb(name, scws, workdir, emin=emin, emax=emax)


def prepare_findgrb(name, scws, workdir, archive_path=None, mask_path=None, emin=15, emax=300):
    workdir = os.path.join(workdir, "FindGRB")
    if os.path.exists(workdir):
        raise ValueError(f"{workdir} already exists")
    if archive_path is None:
        archive_path = "/anita/archivio/scw/"
    if mask_path is None:
        mask_path = f"/zeus1/SRCS/{name}/"
    os.makedirs(workdir)
    os.makedirs(os.path.join(workdir, "scw"))
    os.makedirs(os.path.join(workdir, "exec"))
    os.makedirs(os.path.join(workdir, "log"))
    os.makedirs(os.path.join(workdir, "output"))

    scw_name = name + "_"
    _, scw_lists = create_scw_file(os.path.join(workdir, "scw"), scw_name, scws, maxno=999999)
    shutil.copy(os.path.join(template_path, "run_findgrb.sh"), os.path.join(workdir, "exec", "run.sh"))
    shutil.copy(os.path.join(template_path, "exec_findgrb.sh"), os.path.join(workdir, "exec.sh"))
    with open(os.path.join(template_path, "findgrb.pro")) as f:
        template = f.read()
    template_keys = {
        "TEMPLATE_ARCHIVE": archive_path,
        "TEMPLATE_MASK": mask_path,
        "TEMPLATE_EMIN": emin,
        "TEMPLATE_EMAX": emax,
    }
    for key in template_keys:
        template = template.replace(key, str(template_keys[key]))
    for scw_list in scw_lists:
        exec_file = scw_list.split(".")[0] + ".pro"
        output_name = f"{scw_list.split('.')[0]}_{emin}_{emax}"
        with open(os.path.join(workdir, "exec", exec_file), "w") as f:
            f.write(template.replace("TEMPLATE_SCW", scw_list).replace("TEMPLATE_OUTPUT", output_name))
