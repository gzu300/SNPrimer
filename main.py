import logging

import click

from snprimer import PositionRange
from snprimer import Primer
from snprimer import PrimerPair


@click.group()
def cli():
    pass


@click.command()
@click.option("--vaf", default=0.1, type=float, help="minimum snp vaf to report")
@click.argument("position_file", type=click.File("r"))
@click.argument("output", type=click.File("w"), default="-")
def check(vaf, position_file, output):
    header = ["chr", "start", "end", "found_snp"]
    header_stringify = "\t".join(header)
    output.write(f"{header_stringify}\n")
    for row in position_file.readlines():
        row = [c.strip() for c in row.split("\t")]
        position_range = PositionRange(row[0], row[1], row[2])
        output_line = [position_range.chr, position_range.start, position_range.end]
        output_line.append(str(";".join([snp.rsid for snp in position_range.get_snp(vaf)])))
        output_line += "\n"
        output.write("\t".join(output_line))


@click.command()
@click.option("--snp/--no-snp", default=False, help="Check for the presence of SNP in primer.")
@click.option("--vaf", default=0.1, type=float, help="minimum snp vaf to report")
@click.option("--ref_fasta_file", type=click.Path(exists=True), required=True, help="Path to the reference fasta file.")
@click.option("--ref", type=click.Choice(["hg19", "hg38"], case_sensitive=False), default="hg38")
@click.argument("primer_file", type=click.File("r"))
# Add by position
@click.argument("output", type=click.File("w"), default="-")
def pcr(snp, ref_fasta_file, ref, vaf, primer_file, output):
    header = ["Name", "Left Primer", "Right Primer", "Amplified Region Range", "Amplified Region Seq"]
    if snp:
        header += ["Left Primer SNP", "Right Primer SNP"]
    header_stringify = "\t".join(header)
    output.write(f"{header_stringify}\n")

    logging.info("Start In silico PCR...")

    for line in primer_file.readlines():
        row = [row.strip() for row in line.split("\t")]
        name, l_p, r_p = row[0], Primer(row[1], ref), Primer(row[2], ref)
        primer_pair = PrimerPair(l_p, r_p)
        pcr_hits = primer_pair.make_pcr(ref_fasta_file)
        if len(pcr_hits) > 1:
            logging.warning("Multiple pcr hit for primer pair")
        if pcr_hits:
            for pcr_hit in pcr_hits:
                output_line = (
                    f"{name}\t"
                    f"{l_p.seq}\t"
                    f"{r_p.seq}\t"
                    f"{pcr_hit.name}:{pcr_hit.start}-{pcr_hit.end}\t"
                    f"{pcr_hit.seq}\t"
                )
                if snp:
                    output_line += f"{','.join([snp.rsid for snp in pcr_hit.mate_pair[0].get_snp(vaf)])}\t"
                    output_line += f"{','.join([snp.rsid for snp in pcr_hit.mate_pair[1].get_snp(vaf)])}"
        else:
            output_line = f"{name}\t" f"{l_p.seq}\t" f"{r_p.seq}\t" f"{None}\t" f"{None}\t"
            if snp:
                # TODO make more readable
                pos_l_p = [position_range.get_snp(vaf) for position_range in l_p.position_ranges] or None
                if pos_l_p:
                    output_line += f"{','.join([snp.rsid for snp in pos_l_p[0]])}\t"
                else:
                    output_line += f"{None}\t"
                pos_r_p = [position_range.get_snp(vaf) for position_range in r_p.position_ranges]
                if pos_r_p:
                    output_line += f"{','.join([snp.rsid for snp in pos_r_p[0]])}"
                else:
                    output_line += f"{None}\t"
        output_line += "\n"
        output.write(output_line)


cli.add_command(check)
cli.add_command(pcr)

if __name__ == "__main__":
    cli()


# SNPrimer check primer.tsv --snp
