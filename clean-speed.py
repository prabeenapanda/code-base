# Put the attached script under "~/neutron-cli/src/python/neutroncli/commands/support_utils/feature_update.py" 

@feature_update.command("clean-speed", short_help='Clean speed Attributes')
@click.pass_context
@click.option("-i", "--csv-input-file", help='CSV input file', required=True)
@click.option("-o", "--output-path", help='Output Path', required=True)
@click.option("-r", "--repo-id", help='Repo ID', required=True)
def clean_speed(ctx, csv_input_file, repo_id, output_path):
    if not os.path.isdir(output_path):
        os.makedirs(output_path)

    backup_out_file = open("{}/{}_backup.txt".format(output_path, repo_id), 'w')
    modified_out_file = open("{}/{}_modified_features.txt".format(output_path, repo_id), 'w')

    input_file = open(csv_input_file, 'r')
    if input_file:
        feature_ids = []
        for line in input_file:
            feature_ids.append(line.strip())

    chunked_feature_ids = chunks(feature_ids, 10000)

    for each_batch in chunked_feature_ids:
        query = {
            "filter": {"terms": {"feature_id": each_batch}}
        }
        limit_size = len(each_batch)

        response = ctx.obj.neutron.quark_service.get_features(repo_id, query=query, solr_query=None,
                                                              limit_size=limit_size, hide_deleted=True,
                                                              expand_format="MERGED_FEATURE_CONTAINER", shadow=False,
                                                              overlay_ids=None)

        updated = False
        for feature in response['hits']['hits']:

            feature_id = feature['_source']['FeatureContainerProto']['FeatureProto']['feature_id']
            console.info("Feature in Progress - {}".format(feature_id))

            backup_out_file.write(json.dumps(feature['_source']['FeatureContainerProto']))
            backup_out_file.write("\n")

            try:
                if "road_segment" in feature['_source']['FeatureContainerProto']['FeatureProto']:
                    if "direction" in feature['_source']['FeatureContainerProto']['FeatureProto']['road_segment']:
                        for directions in range(len(feature['_source']['FeatureContainerProto']['FeatureProto']['road_segment']['direction'])):
                            if "speed" in feature['_source']['FeatureContainerProto']['FeatureProto']['road_segment']['direction'][directions]:
                                del feature['_source']['FeatureContainerProto']['FeatureProto']['road_segment']['direction'][directions]['speed']
                                updated = True

            except KeyError as keyError:
                console.error(keyError)
                updated = False

            if updated:
                modified_out_file.write(json.dumps(feature['_source']['FeatureContainerProto']))
                modified_out_file.write("\n")
            else:
                console.error("Features were not updated due to the above exception")

    console.echo("\n\n====================================================================================")
    console.info("Backup featureproto written to {}".format(backup_out_file.name))
    console.info("Modified featureproto written to {}".format(modified_out_file.name))
    console.echo("=====================================================================================\n")
    backup_out_file.close()
    modified_out_file.close()

