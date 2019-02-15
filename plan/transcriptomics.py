# @name: transcriptomics.py
# @description: Module for RNA expression network preparation and management
# @version: 1.0
# @date: 21-01-2019
# @author: Núria Queralt Rosinach
# @email: nuriaqr@scripps.edu

# TO DO:

"""Module for the transcriptomics data"""

import datetime
import pandas as pd
import os
from biothings_client import get_client

# VARIABLES
today = datetime.date.today()

# path to write data
path = os.getcwd() + "/transcriptomics"
if not os.path.isdir(path): os.makedirs(path)


# CHECK NETWORK SCHEMA AND NORMALIZE TO GRAPH SCHEMA
# check network schema
# TODO: check functions

## from regulation/chow/exploratory.ipynb


def read_data():
    """This function reads the raw expression data from a CSV file."""

    # import table S1 (dNGLY1 KO - transcriptomic profile)
    csv_path = '~/workspace/ngly1-graph/regulation/ngly1-fly-chow-2018/data/supp_table_1.csv'
    data_df = pd.read_csv('{}'.format(csv_path))
    print('\n* This is the size of the raw expression data structure: {}'.format(data_df.shape))
    print('* These are the expression attributes: {}'.format(data_df.columns))
    print('* This is the first record:\n{}'.format(data_df.head(1)))

    # save raw data
    path = os.getcwd() + '/transcriptomics/ngly1-fly-chow-2018/data'
    if not os.path.isdir(path): os.makedirs(path)
    data_df.to_csv('{}/supp_table_1.csv'.format(path), index=False)

    return data_df


def clean_data(data_df):
    """This function cleans the raw data structure to the expression attributes of interest to build the graph."""

    # subset [FC 1.5, FDR 5%] (386 = sum(96,290))
    up = data_df.query('log2FoldChange >= 0.57 and padj <= 0.05')
    down = data_df.query('log2FoldChange <= -0.57 and padj <= 0.05')
    up = (up
          [['FlyBase ID', 'Symbol', 'log2FoldChange', 'pvalue', 'padj']]
          # .rename(columns={'log2FoldChange': 'log2FC', 'padj': 'FDR'})
          .reset_index(drop=True)
          .assign(Regulation='Upregulated')
          )
    #up.sort_values(by='log2FoldChange', ascending=False).head(1)
    down = (down
            [['FlyBase ID', 'Symbol', 'log2FoldChange', 'pvalue', 'padj']]
            # .rename(columns={'log2FoldChange': 'log2FC', 'padj': 'FDR'})
            .reset_index(drop=True)
            .assign(Regulation='Downregulated')
            )
    #down.sort_values(by='log2FoldChange', ascending=True).head(1)
    subset_df = pd.concat([up, down])
    print('\n* This is the size of the clean expression data structure: {}'.format(subset_df.shape))
    print('* These are the clean expression attributes: {}'.format(subset_df.columns))
    print('* This is the first record:\n{}'.format(subset_df.head(1)))

    # save subset
    path = os.getcwd() + '/transcriptomics/ngly1-fly-chow-2018/out'
    if not os.path.isdir(path): os.makedirs(path)
    subset_df.to_csv('{}/fc1.5_fdr5_transcriptome_fly.csv'.format(path), index=False)

    #return subset_df


## from regulation/transcriptomics.ipynb

def prepare_data_edges():
    """This function prepares the expression dataset as edges."""

    # read dataset
    csv_path = os.getcwd() + '/transcriptomics/ngly1-fly-chow-2018/out/fc1.5_fdr5_transcriptome_fly.csv'
    chow = pd.read_csv('{}'.format(csv_path))
    print('\n* This is the size of the expression data structure: {}'.format(chow.shape))
    print('* These are the expression attributes: {}'.format(chow.columns))
    print('* This is the first record:\n{}'.format(chow.head(1)))

    # prepare edges
    chow = (chow
            .rename(columns={'FlyBase ID': 'flybase_id', 'Symbol': 'symbol', 'Regulation': 'regulation'})
            .assign(source='Chow')
            .assign(subject_id='FlyBase:FBgn0033050')
            .assign(subject_label='Pngl')
            .assign(property_id='RO:0002434')
            .assign(property_label='interacts with')
            .assign(reference_id='PMID:29346549')
            )
    chow['object_id'] = chow.flybase_id.apply(lambda x: 'FlyBase:' + str(x))
    
    # save individual dataset edges
    path = os.getcwd() + '/transcriptomics/ngly1-fly-chow-2018/out'
    if not os.path.isdir(path): os.makedirs(path)
    chow.to_csv('{}/chow_fc1.5_fdr5_transcriptome_fly_edges.csv'.format(path), index=False)

    #return chow


def prepare_rna_edges():
    """This function prepares and compiles all individual data edges into RNA edges to build the graph."""

    # read individual datasets
    csv_path = os.getcwd() + '/transcriptomics/ngly1-fly-chow-2018/out/chow_fc1.5_fdr5_transcriptome_fly_edges.csv'
    chow = pd.read_csv('{}'.format(csv_path))
    print('\n* This is the size of the expression data structure: {}'.format(chow.shape))
    print('* These are the expression attributes: {}'.format(chow.columns))
    print('* This is the first record:\n{}'.format(chow.head(1)))

    # select and rename key columns
    chow = (chow
            [['symbol', 'log2FoldChange', 'pvalue', 'padj',
              'regulation', 'source', 'subject_id', 'subject_label', 'property_id',
              'property_label', 'reference_id', 'object_id']]
            .rename(columns={'symbol': 'object_label', 'padj': 'fdr'})

            )

    # reorder columns
    chow = chow[['subject_id', 'subject_label', 'property_id',
                 'property_label', 'object_id', 'object_label', 'log2FoldChange', 'pvalue', 'fdr', 'regulation',
                 'source', 'reference_id']]
    # concat edges
    edges = pd.concat([chow, pd.DataFrame()], ignore_index=True)

    # drop duplicates
    edges.drop_duplicates(inplace=True)

    # print edges info
    print('\n* This is the size of the edges data structure: {}'.format(edges.shape))
    print('* These are the edges attributes: {}'.format(edges.columns))
    print('* This is the first record:\n{}'.format(edges.head(1)))

    return edges



# BUILD NETWORK

def build_edges(edges):
    """This function builds the edges network file."""

    # give graph format
    curie_dct = {
        'ro': 'http://purl.obolibrary.org/obo/',
        'pmid': 'https://www.ncbi.nlm.nih.gov/pubmed/',
        'encode': 'https://www.encodeproject.org/search/?searchTerm='
    }

    edges_l = list()
    for i, row in edges.iterrows():
        # property uri: http://purl.obolibrary.org/obo/RO_0002434
        property_uri = 'NA'
        if ':' in row['property_id']:
            property_uri = curie_dct[row['property_id'].split(':')[0].lower()] + row['property_id'].replace(':', '_')

        # reference_uri: https://www.ncbi.nlm.nih.gov/pubmed/25416956
        # capture nan or None values, i.e. all possible nulls
        if (isinstance(row['reference_id'], float) and str(row['reference_id']).lower() == 'nan') or row[
            'reference_id'] is None:
            row['reference_id'] = 'NA'
        if ':' not in row['reference_id']:
            reference_uri = row['reference_id']
        else:
            try:
                reference_uri = curie_dct[row['reference_id'].split(':')[0].lower()] + row['reference_id'].split(':')[1]
            except KeyError:
                reference_uri = row['reference_id']
                print('There is a reference curie with and unrecognized namespace:', row['reference_id'])
        # build list of edges as list of dict, i.e a df, where a dict is an edge
        edge = dict()
        edge['subject_id'] = row['subject_id']
        edge['object_id'] = row['object_id']
        edge['property_id'] = row['property_id']
        edge['property_label'] = row['property_label']
        edge['property_description'] = 'NA'
        edge['property_uri'] = property_uri
        edge['reference_uri'] = reference_uri
        edge[
            'reference_supporting_text'] = 'To understand how loss of NGLY1 contributes to disease, we developed a Drosophila model of NGLY1 deficiency. Loss of NGLY1 function resulted in developmental delay and lethality. We used RNAseq to determine which processes are misregulated in the absence of NGLY1.' if \
        row['source'] == 'Chow' else 'This edge comes from the RNA-seq profile dataset extracted by the XXX Lab YYYY.'
        edge['reference_date'] = '2018-03-15' if row['source'] == 'Chow' else 'NA'
        edges_l.append(edge)

    # save edges file
    path = os.getcwd() + '/graph'
    if not os.path.isdir(path): os.makedirs(path)
    pd.DataFrame(edges_l).fillna('NA').to_csv('{}/rna_edges_v{}.csv'.format(path,today), index=False)

    # print edges info
    print('\n* This is the size of the edges file data structure: {}'.format(pd.DataFrame(edges_l).shape))
    print('* These are the edges attributes: {}'.format(pd.DataFrame(edges_l).columns))
    print('* This is the first record:\n{}'.format(pd.DataFrame(edges_l).head(1)))

    #return


def build_nodes(edges):
    """This function builds the nodes network file."""

    # retrieve node attributes from biothings and build dictionary
    # from biothings we retrieve: name (new attribute for short description), alias (synonyms), summary (description).
    # symbols in this case come from the original source. otherwise are gonna be retrieved from biothings as well.
    # build concept dict: {id:symbol}
    concept_dct = dict()
    for i, row in edges.iterrows():
        # node for subject
        concept_dct[row['subject_id']] = {'preflabel': row['subject_label']}
        # node for object
        concept_dct[row['object_id']] = {'preflabel': row['object_label']}
    print('* Total number of nodes: {}'.format(len(concept_dct.keys())))

    # biothings api + dictionaries
    # input list for api: since by id we have flybase, hgnc/entrez or ensembl, i am gonna use symbol
    symbols = list()
    for idx, symbol in concept_dct.items():
        # id = key.split(':')[1] if ':' in key else key
        symbols.append(symbol['preflabel'])

    #print(symbols[0:5])
    #len(symbols)

    # api call
    mg = get_client('gene')
    df = mg.querymany(symbols, scopes='symbol,alias', fields='alias,name,summary', size=1, as_dataframe=True)
    #df.head(2)
    #print(df.shape)
    #print(len(concept_dct.keys()))

    # dictionaries {id: {name:, alias:, summary:}}
    i = 0
    #print(len(concept_dct))
    for symbol, row in df.iterrows():
        # associate concept to symbol
        for concept in concept_dct:
            if concept_dct[concept]['preflabel'] == symbol:
                i += 1
                # add attributes
                concept_dct[concept]['name'] = row['name']
                concept_dct[concept]['synonyms'] = row['alias']
                concept_dct[concept]['description'] = row['summary']

    # build a list of nodes as list of dict, i.e a df, where a dict is a node
    nodes_l = list()
    for concept in concept_dct:
        # node for subject
        node = dict()
        node['id'] = concept
        node['semantic_groups'] = 'GENE'
        node['preflabel'] = concept_dct[concept]['preflabel']
        node['name'] = concept_dct[concept]['name']
        node['synonyms'] = '|'.join(list(concept_dct[concept]['synonyms'])) if isinstance(
            concept_dct[concept]['synonyms'], list) else concept_dct[concept]['synonyms']
        node['description'] = concept_dct[concept]['description']
        nodes_l.append(node)

    # save nodes file
    pd.DataFrame(nodes_l).fillna('NA').to_csv('./graph/rna_nodes_v{}.csv'.format(today), index=False)

    # print nodes info
    print('\n* This is the size of the nodes file data structure: {}'.format(pd.DataFrame(nodes_l).shape))
    print('* These are the nodes attributes: {}'.format(pd.DataFrame(nodes_l).columns))
    print('* This is the first record:\n{}'.format(pd.DataFrame(nodes_l).head(1)))

    # return

# NETWORK MANAGEMENT FUNCTIONS


def print_nodes(nodes, filename):
    """This function save nodes into a CSV file."""

    # print output file

    #return

if __name__ == '__main__':

    # prepare data to graph schema
    data = read_data()
    clean_data(data)
    prepare_data_edges()
    edges = prepare_rna_edges()

    # build network
    build_edges(edges)
    build_nodes(edges)