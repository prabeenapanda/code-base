def fix_fow_attributes(ctx, csv_input_file, repo_id, output_path, attribute_changes):
    """
    This is to modify different road_segment attributes based on the form_of_way values.
    Expected input format for attribute-changes csv file :

    "attribute,fow,value"

    Supported attributes - ["surface_material", "undetermined_path", "elevated_roadway",
    "is_multiply_digitized", "is_bicycle_navigable", "is_navigable"]

    """

    def stringtobool(str):
        return str.lower() == "true"

    attribute_file_format = "attribute,fow,value"
    if click.confirm("\nPlease verify the attribute-change csv file have the Expected format - [{}]"
                     "\nPlease confirm - ".format(attribute_file_format)):
        pass
    else:
        console.error("Please correct the attribute-change csv file format and try again !!")
        return

    attribute_changes_json = {
        "surface_material": [],
        "undetermined_path": [],
        "elevated_roadway": [],
        "is_multiply_digitized": [],
        "is_bicycle_navigable": [],
        "is_navigable": []
    }

    attribute_file = open(attribute_changes, 'r')
    if attribute_file:
        headers = [header.strip() for header in next(attribute_file).split(",")[1:]]
        for line in attribute_file:
            line = bytes(line, 'utf-8').decode('utf-8', 'ignore')
            properties = [value.strip() for value in line.split(",")]
            if properties[0] in attribute_changes_json.keys():
                attribute_changes_json[properties[0]].append(dict(zip(headers, properties[1:])))

    if not os.path.isdir(output_path):
        os.makedirs(output_path)

    backup_out_file = open("{}/{}_backup.txt".format(output_path, repo_id), 'w')
    modified_out_file = open("{}/{}_modified_features.txt".format(output_path, repo_id), 'w')

    input_file = open(csv_input_file, 'r')
    if input_file:
        feature_ids = []
        for line in input_file:
            feature_ids.append(line.strip())

    direction_attributes = ["is_bicycle_navigable", "is_navigable"]

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

                    for attribute in attribute_changes_json.keys():
                        for attribute_index in range(len(attribute_changes_json[attribute])):
                            if attribute_changes_json[attribute][attribute_index]['value'] in ["True", "False"]:
                                attribute_changes_json[attribute][attribute_index]['value'] = stringtobool(attribute_changes_json[attribute][attribute_index]['value'])

                            if attribute_changes_json[attribute][attribute_index]['fow'] == "all":
                                feature['_source']['FeatureContainerProto']['FeatureProto']['road_segment'][
                                    attribute] = attribute_changes_json[attribute][attribute_index]['value']

                            elif attribute_changes_json[attribute][attribute_index]['fow'] in ["all(if not already True)", "all(for null values only)"]:
                                if attribute not in feature['_source']['FeatureContainerProto']['FeatureProto']['road_segment']:
                                    feature['_source']['FeatureContainerProto']['FeatureProto']['road_segment'][attribute] = attribute_changes_json[attribute][attribute_index]['value']
                                else:
                                    if not feature['_source']['FeatureContainerProto']['FeatureProto']['road_segment'][attribute]:
                                        feature['_source']['FeatureContainerProto']['FeatureProto']['road_segment'][
                                            attribute] = attribute_changes_json[attribute][attribute_index]['value']

                            else:
                                if "form_of_way" in feature['_source']['FeatureContainerProto']['FeatureProto']['road_segment']:

                                    if feature['_source']['FeatureContainerProto']['FeatureProto']['road_segment']['form_of_way'] == attribute_changes_json[attribute][attribute_index]['fow']:
                                        if attribute not in direction_attributes:
                                            feature['_source']['FeatureContainerProto']['FeatureProto']['road_segment'][
                                                'road_surface'] = {attribute: attribute_changes_json[attribute][attribute_index]['value']}
                                        else:
                                            if "direction" in feature['_source']['FeatureContainerProto']['FeatureProto']['road_segment']:
                                                for direction_index in range(len(feature['_source']['FeatureContainerProto']['FeatureProto']['road_segment']['direction'])):
                                                    feature['_source']['FeatureContainerProto']['FeatureProto']['road_segment'][
                                                        'direction'][direction_index][attribute] = attribute_changes_json[attribute][attribute_index]['value']

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