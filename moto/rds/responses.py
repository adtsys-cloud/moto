from __future__ import unicode_literals
from collections import defaultdict

from moto.core.responses import BaseResponse
from moto.ec2.models import ec2_backends
from .models import rds_backends
from .exceptions import DBParameterGroupNotFoundError
import pdb

class RDSResponse(BaseResponse):

    @property
    def backend(self):
        return rds_backends[self.region]

    def _get_db_kwargs(self):
        args = {
            "auto_minor_version_upgrade": self._get_param('AutoMinorVersionUpgrade'),
            "allocated_storage": self._get_int_param('AllocatedStorage'),
            "availability_zone": self._get_param("AvailabilityZone"),
            "backup_retention_period": self._get_param("BackupRetentionPeriod"),
            "db_instance_class": self._get_param('DBInstanceClass'),
            "db_instance_identifier": self._get_param('DBInstanceIdentifier'),
            "db_name": self._get_param("DBName"),
            "db_parameter_group_name": self._get_param("DBParameterGroupName"),
            "db_subnet_group_name": self._get_param("DBSubnetGroupName"),
            "engine": self._get_param("Engine"),
            "engine_version": self._get_param("EngineVersion"),
            "iops": self._get_int_param("Iops"),
            "kms_key_id": self._get_param("KmsKeyId"),
            "master_user_password": self._get_param('MasterUserPassword'),
            "master_username": self._get_param('MasterUsername'),
            "multi_az": self._get_bool_param("MultiAZ"),
            # OptionGroupName
            "option_group_name": self._get_param('OptionGroupName'),
            "port": self._get_param('Port'),
            # PreferredBackupWindow
            # PreferredMaintenanceWindow
            "publicly_accessible": self._get_param("PubliclyAccessible"),
            "region": self.region,
            "security_groups": self._get_multi_param('DBSecurityGroups.DBSecurityGroupName'),
            "storage_encrypted": self._get_param("StorageEncrypted"),
            "storage_type": self._get_param("StorageType"),
            # VpcSecurityGroupIds.member.N
            "tags": list(),
        }
        args['tags'] = self.unpack_complex_list_params(
            'Tags.Tag', ('Key', 'Value'))
        return args

    def _get_db_replica_kwargs(self):
        return {
            "auto_minor_version_upgrade": self._get_param('AutoMinorVersionUpgrade'),
            "availability_zone": self._get_param("AvailabilityZone"),
            "db_instance_class": self._get_param('DBInstanceClass'),
            "db_instance_identifier": self._get_param('DBInstanceIdentifier'),
            "db_subnet_group_name": self._get_param("DBSubnetGroupName"),
            "iops": self._get_int_param("Iops"),
            # OptionGroupName
            "port": self._get_param('Port'),
            "publicly_accessible": self._get_param("PubliclyAccessible"),
            "source_db_identifier": self._get_param('SourceDBInstanceIdentifier'),
            "storage_type": self._get_param("StorageType"),
        }

    def _get_option_group_kwargs(self):
        return {
            'major_engine_version': self._get_param('MajorEngineVersion'),
            'description': self._get_param('OptionGroupDescription'),
            'engine_name': self._get_param('EngineName'),
            'name': self._get_param('OptionGroupName')
        }

    def _get_db_parameter_group_kwargs(self):
        return {
            'description': self._get_param('Description'),
            'family': self._get_param('DBParameterGroupFamily'),
            'name': self._get_param('DBParameterGroupName'),
            'tags': self.unpack_complex_list_params('Tags.Tag', ('Key', 'Value')),
        }

    def unpack_complex_list_params(self, label, names):
        unpacked_list = list()
        count = 1
        while self._get_param('{0}.{1}.{2}'.format(label, count, names[0])):
            param = dict()
            for i in range(len(names)):
                param[names[i]] = self._get_param(
                    '{0}.{1}.{2}'.format(label, count, names[i]))
            unpacked_list.append(param)
            count += 1
        return unpacked_list

    def unpack_list_params(self, label):
        unpacked_list = list()
        count = 1
        while self._get_param('{0}.{1}'.format(label, count)):
            unpacked_list.append(self._get_param(
                '{0}.{1}'.format(label, count)))
            count += 1
        return unpacked_list

    def create_db_instance(self):
        db_kwargs = self._get_db_kwargs()
        database = self.backend.create_database(db_kwargs)
        template = self.response_template(CREATE_DATABASE_TEMPLATE)
        return template.render(database=database)

    def create_db_instance_read_replica(self):
        db_kwargs = self._get_db_replica_kwargs()

        database = self.backend.create_database_replica(db_kwargs)
        template = self.response_template(CREATE_DATABASE_REPLICA_TEMPLATE)
        return template.render(database=database)

    def describe_db_instances(self):
        db_instance_identifier = self._get_param('DBInstanceIdentifier')
        databases = self.backend.describe_databases(db_instance_identifier)
        template = self.response_template(DESCRIBE_DATABASES_TEMPLATE)
        response = template.render(databases=databases)
        if len(databases) == 1 and databases[0].status == "modifying":
          db_kwargs = {"status": "available"}
          self.backend.modify_database(db_instance_identifier, db_kwargs)
        return response

    def modify_db_instance(self):
        db_instance_identifier = self._get_param('DBInstanceIdentifier')
        db_kwargs = self._get_db_kwargs()
        db_kwargs["status"] = "modifying"
        database = self.backend.modify_database(
            db_instance_identifier, db_kwargs)
        template = self.response_template(MODIFY_DATABASE_TEMPLATE)
        return template.render(database=database)

    def delete_db_instance(self):
        db_instance_identifier = self._get_param('DBInstanceIdentifier')
        database = self.backend.delete_database(db_instance_identifier)
        template = self.response_template(DELETE_DATABASE_TEMPLATE)
        return template.render(database=database)

    def reboot_db_instance(self):
        db_instance_identifier = self._get_param('DBInstanceIdentifier')
        database = self.backend.reboot_db_instance(db_instance_identifier)
        template = self.response_template(REBOOT_DATABASE_TEMPLATE)
        return template.render(database=database)

    def list_tags_for_resource(self):
        arn = self._get_param('ResourceName')
        template = self.response_template(LIST_TAGS_FOR_RESOURCE_TEMPLATE)
        tags = self.backend.list_tags_for_resource(arn)
        return template.render(tags=tags)

    def add_tags_to_resource(self):
        arn = self._get_param('ResourceName')
        tags = self.unpack_complex_list_params('Tags.Tag', ('Key', 'Value'))
        tags = self.backend.add_tags_to_resource(arn, tags)
        template = self.response_template(ADD_TAGS_TO_RESOURCE_TEMPLATE)
        return template.render(tags=tags)

    def remove_tags_from_resource(self):
        arn = self._get_param('ResourceName')
        tag_keys = self.unpack_list_params('TagKeys.member')
        self.backend.remove_tags_from_resource(arn, tag_keys)
        template = self.response_template(REMOVE_TAGS_FROM_RESOURCE_TEMPLATE)
        return template.render()

    def create_db_security_group(self):
        group_name = self._get_param('DBSecurityGroupName')
        description = self._get_param('DBSecurityGroupDescription')
        tags = self.unpack_complex_list_params('Tags.Tag', ('Key', 'Value'))
        security_group = self.backend.create_security_group(
            group_name, description, tags)
        template = self.response_template(CREATE_SECURITY_GROUP_TEMPLATE)
        return template.render(security_group=security_group)

    def describe_db_security_groups(self):
        security_group_name = self._get_param('DBSecurityGroupName')
        security_groups = self.backend.describe_security_groups(
            security_group_name)
        template = self.response_template(DESCRIBE_SECURITY_GROUPS_TEMPLATE)
        return template.render(security_groups=security_groups)

    def delete_db_security_group(self):
        security_group_name = self._get_param('DBSecurityGroupName')
        security_group = self.backend.delete_security_group(
            security_group_name)
        template = self.response_template(DELETE_SECURITY_GROUP_TEMPLATE)
        return template.render(security_group=security_group)

    def authorize_db_security_group_ingress(self):
        security_group_name = self._get_param('DBSecurityGroupName')
        cidr_ip = self._get_param('CIDRIP')
        security_group = self.backend.authorize_security_group(
            security_group_name, cidr_ip)
        template = self.response_template(AUTHORIZE_SECURITY_GROUP_TEMPLATE)
        return template.render(security_group=security_group)

    def create_db_subnet_group(self):
        subnet_name = self._get_param('DBSubnetGroupName')
        description = self._get_param('DBSubnetGroupDescription')
        subnet_ids = self._get_multi_param('SubnetIds.SubnetIdentifier')
        tags = self.unpack_complex_list_params('Tags.Tag', ('Key', 'Value'))
        subnets = [ec2_backends[self.region].get_subnet(
            subnet_id) for subnet_id in subnet_ids]
        subnet_group = self.backend.create_subnet_group(
            subnet_name, description, subnets, tags)
        template = self.response_template(CREATE_SUBNET_GROUP_TEMPLATE)
        return template.render(subnet_group=subnet_group)

    def describe_db_subnet_groups(self):
        subnet_name = self._get_param('DBSubnetGroupName')
        subnet_groups = self.backend.describe_subnet_groups(subnet_name)
        template = self.response_template(DESCRIBE_SUBNET_GROUPS_TEMPLATE)
        return template.render(subnet_groups=subnet_groups)

    def delete_db_subnet_group(self):
        subnet_name = self._get_param('DBSubnetGroupName')
        subnet_group = self.backend.delete_subnet_group(subnet_name)
        template = self.response_template(DELETE_SUBNET_GROUP_TEMPLATE)
        return template.render(subnet_group=subnet_group)

    def create_option_group(self):
        kwargs = self._get_option_group_kwargs()
        option_group = self.backend.create_option_group(kwargs)
        template = self.response_template(CREATE_OPTION_GROUP_TEMPLATE)
        return template.render(option_group=option_group)

    def delete_option_group(self):
        kwargs = self._get_option_group_kwargs()
        option_group = self.backend.delete_option_group(kwargs['name'])
        template = self.response_template(DELETE_OPTION_GROUP_TEMPLATE)
        return template.render(option_group=option_group)

    def describe_option_groups(self):
        kwargs = self._get_option_group_kwargs()
        kwargs['max_records'] = self._get_param('MaxRecords')
        kwargs['marker'] = self._get_param('Marker')
        option_groups = self.backend.describe_option_groups(kwargs)
        template = self.response_template(DESCRIBE_OPTION_GROUP_TEMPLATE)
        return template.render(option_groups=option_groups)

    def describe_option_group_options(self):
        engine_name = self._get_param('EngineName')
        major_engine_version = self._get_param('MajorEngineVersion')
        option_group_options = self.backend.describe_option_group_options(
            engine_name, major_engine_version)
        return option_group_options

    def modify_option_group(self):
        option_group_name = self._get_param('OptionGroupName')
        count = 1
        options_to_include = []
        while self._get_param('OptionsToInclude.OptionConfiguration.{0}.OptionName'.format(count)):
            options_to_include.append({
                'Port': self._get_param('OptionsToInclude.OptionConfiguration.{0}.Port'.format(count)),
                'OptionName': self._get_param('OptionsToInclude.OptionConfiguration.{0}.OptionName'.format(count)),
                'DBSecurityGroupMemberships': self._get_param('OptionsToInclude.OptionConfiguration.{0}.DBSecurityGroupMemberships'.format(count)),
                'OptionSettings': self._get_param('OptionsToInclude.OptionConfiguration.{0}.OptionSettings'.format(count)),
                'VpcSecurityGroupMemberships': self._get_param('OptionsToInclude.OptionConfiguration.{0}.VpcSecurityGroupMemberships'.format(count))
            })
            count += 1

        count = 1
        options_to_remove = []
        while self._get_param('OptionsToRemove.OptionConfiguration.{0}'.format(count)):
            options_to_remove.append(self._get_param(
                'OptionsToRemove.OptionConfiguration.{0}'.format(count)))
            count += 1
        apply_immediately = self._get_param('ApplyImmediately')
        option_group = self.backend.modify_option_group(option_group_name,
                                                        options_to_include,
                                                        options_to_remove,
                                                        apply_immediately)
        template = self.response_template(MODIFY_OPTION_GROUP_TEMPLATE)
        return template.render(option_group=option_group)

    def create_db_parameter_group(self):
        kwargs = self._get_db_parameter_group_kwargs()
        db_parameter_group = self.backend.create_db_parameter_group(kwargs)
        template = self.response_template(CREATE_DB_PARAMETER_GROUP_TEMPLATE)
        return template.render(db_parameter_group=db_parameter_group)

    def describe_db_parameter_groups(self):
        kwargs = self._get_db_parameter_group_kwargs()
        kwargs['max_records'] = self._get_param('MaxRecords')
        kwargs['marker'] = self._get_param('Marker')
        db_parameter_groups = self.backend.describe_db_parameter_groups(kwargs)
        template = self.response_template(
            DESCRIBE_DB_PARAMETER_GROUPS_TEMPLATE)
        return template.render(db_parameter_groups=db_parameter_groups)

    def modify_db_parameter_group(self):
        db_parameter_group_name = self._get_param('DBParameterGroupName')
        db_parameter_group_parameters = self._get_db_parameter_group_paramters()
        db_parameter_group = self.backend.modify_db_parameter_group(db_parameter_group_name,
                                                                    db_parameter_group_parameters)
        template = self.response_template(MODIFY_DB_PARAMETER_GROUP_TEMPLATE)
        return template.render(db_parameter_group=db_parameter_group)

    def _get_db_parameter_group_paramters(self):
        parameter_group_parameters = defaultdict(dict)
        for param_name, value in self.querystring.items():
            if not param_name.startswith('Parameters.Parameter'):
                continue

            split_param_name = param_name.split('.')
            param_id = split_param_name[2]
            param_setting = split_param_name[3]

            parameter_group_parameters[param_id][param_setting] = value[0]

        return parameter_group_parameters.values()

    def describe_db_parameters(self):
        db_parameter_group_name = self._get_param('DBParameterGroupName')
        db_parameter_groups = self.backend.describe_db_parameter_groups(
            {'name': db_parameter_group_name})
        if not db_parameter_groups:
            raise DBParameterGroupNotFoundError(db_parameter_group_name)

        template = self.response_template(DESCRIBE_DB_PARAMETERS_TEMPLATE)
        return template.render(db_parameter_group=db_parameter_groups[0])

    def delete_db_parameter_group(self):
        kwargs = self._get_db_parameter_group_kwargs()
        db_parameter_group = self.backend.delete_db_parameter_group(kwargs[
                                                                    'name'])
        template = self.response_template(DELETE_DB_PARAMETER_GROUP_TEMPLATE)
        return template.render(db_parameter_group=db_parameter_group)

    def restore_db_instance_from_db_snapshot(self):
        default_engine_versions = {
            "MySQL": "5.6.21",
            "mysql": "5.6.21",
            "oracle-se2": "12.1.0.2.v7",
            "oracle-se1": "11.2.0.4.v3",
            "oracle-se": "11.2.0.4.v3",
            "oracle-ee": "11.2.0.4.v3",
            "sqlserver-ee": "11.00.2100.60.v1",
            "sqlserver-se": "11.00.2100.60.v1",
            "sqlserver-ex": "11.00.2100.60.v1",
            "sqlserver-web": "11.00.2100.60.v1",
            "postgres": "9.3.3"
        }
        db_kwargs = self._get_db_kwargs()
        db_engine_version = default_engine_versions[db_kwargs["engine"]]
        db_kwargs["engine_version"] = db_engine_version
        db_kwargs["allocated_storage"] = 15
        db_kwargs["db_snapshot_identifier"] = self._get_param('DBSnapshotIdentifier')
        database = self.backend.create_database(db_kwargs)
        template = self.response_template(RESTORE_DB_INSTANCE_FROM_DB_SNAPSHOT_TEMPLATE)
        return template.render(database=database)

CREATE_DATABASE_TEMPLATE = """<CreateDBInstanceResponse xmlns="http://rds.amazonaws.com/doc/2014-09-01/">
  <CreateDBInstanceResult>
  {{ database.to_xml() }}
  </CreateDBInstanceResult>
  <ResponseMetadata>
    <RequestId>523e3218-afc7-11c3-90f5-f90431260ab4</RequestId>
  </ResponseMetadata>
</CreateDBInstanceResponse>"""

CREATE_DATABASE_REPLICA_TEMPLATE = """<CreateDBInstanceReadReplicaResponse xmlns="http://rds.amazonaws.com/doc/2014-09-01/">
  <CreateDBInstanceReadReplicaResult>
  {{ database.to_xml() }}
  </CreateDBInstanceReadReplicaResult>
  <ResponseMetadata>
    <RequestId>5e60c46d-a844-11e4-bb68-17f36418e58f</RequestId>
  </ResponseMetadata>
</CreateDBInstanceReadReplicaResponse>"""

DESCRIBE_DATABASES_TEMPLATE = """<DescribeDBInstancesResponse xmlns="http://rds.amazonaws.com/doc/2014-09-01/">
  <DescribeDBInstancesResult>
    <DBInstances>
    {%- for database in databases -%}
      {{ database.to_xml() }}
    {%- endfor -%}
    </DBInstances>
  </DescribeDBInstancesResult>
  <ResponseMetadata>
    <RequestId>523e3218-afc7-11c3-90f5-f90431260ab4</RequestId>
  </ResponseMetadata>
</DescribeDBInstancesResponse>"""

MODIFY_DATABASE_TEMPLATE = """<ModifyDBInstanceResponse xmlns="http://rds.amazonaws.com/doc/2014-09-01/">
  <ModifyDBInstanceResult>
  {{ database.to_xml() }}
  </ModifyDBInstanceResult>
  <ResponseMetadata>
    <RequestId>bb58476c-a1a8-11e4-99cf-55e92d4bbada</RequestId>
  </ResponseMetadata>
</ModifyDBInstanceResponse>"""

REBOOT_DATABASE_TEMPLATE = """<RebootDBInstanceResponse xmlns="http://rds.amazonaws.com/doc/2014-09-01/">
  <RebootDBInstanceResult>
  {{ database.to_xml() }}
  </RebootDBInstanceResult>
  <ResponseMetadata>
    <RequestId>d55711cb-a1ab-11e4-99cf-55e92d4bbada</RequestId>
  </ResponseMetadata>
</RebootDBInstanceResponse>"""


DELETE_DATABASE_TEMPLATE = """<DeleteDBInstanceResponse xmlns="http://rds.amazonaws.com/doc/2014-09-01/">
  <DeleteDBInstanceResult>
    {{ database.to_xml() }}
  </DeleteDBInstanceResult>
  <ResponseMetadata>
    <RequestId>7369556f-b70d-11c3-faca-6ba18376ea1b</RequestId>
  </ResponseMetadata>
</DeleteDBInstanceResponse>"""

CREATE_SECURITY_GROUP_TEMPLATE = """<CreateDBSecurityGroupResponse xmlns="http://rds.amazonaws.com/doc/2014-09-01/">
  <CreateDBSecurityGroupResult>
  {{ security_group.to_xml() }}
  </CreateDBSecurityGroupResult>
  <ResponseMetadata>
    <RequestId>462165d0-a77a-11e4-a5fa-75b30c556f97</RequestId>
  </ResponseMetadata>
</CreateDBSecurityGroupResponse>"""

DESCRIBE_SECURITY_GROUPS_TEMPLATE = """<DescribeDBSecurityGroupsResponse xmlns="http://rds.amazonaws.com/doc/2014-09-01/">
  <DescribeDBSecurityGroupsResult>
    <DBSecurityGroups>
    {% for security_group in security_groups %}
      {{ security_group.to_xml() }}
    {% endfor %}
   </DBSecurityGroups>
  </DescribeDBSecurityGroupsResult>
  <ResponseMetadata>
    <RequestId>5df2014e-a779-11e4-bdb0-594def064d0c</RequestId>
  </ResponseMetadata>
</DescribeDBSecurityGroupsResponse>"""

DELETE_SECURITY_GROUP_TEMPLATE = """<DeleteDBSecurityGroupResponse xmlns="http://rds.amazonaws.com/doc/2014-09-01/">
  <ResponseMetadata>
    <RequestId>97e846bd-a77d-11e4-ac58-91351c0f3426</RequestId>
  </ResponseMetadata>
</DeleteDBSecurityGroupResponse>"""

AUTHORIZE_SECURITY_GROUP_TEMPLATE = """<AuthorizeDBSecurityGroupIngressResponse xmlns="http://rds.amazonaws.com/doc/2014-09-01/">
  <AuthorizeDBSecurityGroupIngressResult>
  {{ security_group.to_xml() }}
  </AuthorizeDBSecurityGroupIngressResult>
  <ResponseMetadata>
    <RequestId>75d32fd5-a77e-11e4-8892-b10432f7a87d</RequestId>
  </ResponseMetadata>
</AuthorizeDBSecurityGroupIngressResponse>"""

CREATE_SUBNET_GROUP_TEMPLATE = """<CreateDBSubnetGroupResponse xmlns="http://rds.amazonaws.com/doc/2014-09-01/">
  <CreateDBSubnetGroupResult>
  {{ subnet_group.to_xml() }}
  </CreateDBSubnetGroupResult>
  <ResponseMetadata>
    <RequestId>3a401b3f-bb9e-11d3-f4c6-37db295f7674</RequestId>
  </ResponseMetadata>
</CreateDBSubnetGroupResponse>"""

DESCRIBE_SUBNET_GROUPS_TEMPLATE = """<DescribeDBSubnetGroupsResponse xmlns="http://rds.amazonaws.com/doc/2014-09-01/">
  <DescribeDBSubnetGroupsResult>
    <DBSubnetGroups>
    {% for subnet_group in subnet_groups %}
      {{ subnet_group.to_xml() }}
    {% endfor %}
    </DBSubnetGroups>
  </DescribeDBSubnetGroupsResult>
  <ResponseMetadata>
    <RequestId>b783db3b-b98c-11d3-fbc7-5c0aad74da7c</RequestId>
  </ResponseMetadata>
</DescribeDBSubnetGroupsResponse>"""

DELETE_SUBNET_GROUP_TEMPLATE = """<DeleteDBSubnetGroupResponse xmlns="http://rds.amazonaws.com/doc/2014-09-01/">
  <ResponseMetadata>
    <RequestId>13785dd5-a7fc-11e4-bb9c-7f371d0859b0</RequestId>
  </ResponseMetadata>
</DeleteDBSubnetGroupResponse>"""

CREATE_OPTION_GROUP_TEMPLATE = """<CreateOptionGroupResponse xmlns="http://rds.amazonaws.com/doc/2014-09-01/">
  <CreateOptionGroupResult>
  {{ option_group.to_xml() }}
  </CreateOptionGroupResult>
  <ResponseMetadata>
    <RequestId>1e38dad4-9f50-11e4-87ea-a31c60ed2e36</RequestId>
  </ResponseMetadata>
</CreateOptionGroupResponse>"""

DELETE_OPTION_GROUP_TEMPLATE = """<DeleteOptionGroupResponse xmlns="http://rds.amazonaws.com/doc/2014-09-01/">
  <ResponseMetadata>
    <RequestId>e2590367-9fa2-11e4-99cf-55e92d41c60e</RequestId>
  </ResponseMetadata>
</DeleteOptionGroupResponse>"""

DESCRIBE_OPTION_GROUP_TEMPLATE = """<DescribeOptionGroupsResponse xmlns="http://rds.amazonaws.com/doc/2014-09-01/">
  <DescribeOptionGroupsResult>
    <OptionGroupsList>
    {%- for option_group in option_groups -%}
      {{ option_group.to_xml() }}
    {%- endfor -%}
    </OptionGroupsList>
  </DescribeOptionGroupsResult>
  <ResponseMetadata>
    <RequestId>4caf445d-9fbc-11e4-87ea-a31c60ed2e36</RequestId>
  </ResponseMetadata>
</DescribeOptionGroupsResponse>"""

DESCRIBE_OPTION_GROUP_OPTIONS_TEMPLATE = """<DescribeOptionGroupOptionsResponse xmlns="http://rds.amazonaws.com/doc/2014-09-01/">
  <DescribeOptionGroupOptionsResult>
    <OptionGroupOptions>
    {%- for option_group_option in option_group_options -%}
      {{ option_group_option.to_xml() }}
    {%- endfor -%}
    </OptionGroupOptions>
  </DescribeOptionGroupOptionsResult>
  <ResponseMetadata>
    <RequestId>457f7bb8-9fbf-11e4-9084-5754f80d5144</RequestId>
  </ResponseMetadata>
</DescribeOptionGroupOptionsResponse>"""

MODIFY_OPTION_GROUP_TEMPLATE = """<ModifyOptionGroupResponse xmlns="http://rds.amazonaws.com/doc/2014-09-01/">
  <ModifyOptionGroupResult>
    {{ option_group.to_xml() }}
  </ModifyOptionGroupResult>
  <ResponseMetadata>
    <RequestId>ce9284a5-a0de-11e4-b984-a11a53e1f328</RequestId>
  </ResponseMetadata>
</ModifyOptionGroupResponse>"""

CREATE_DB_PARAMETER_GROUP_TEMPLATE = """<CreateDBParameterGroupResponse xmlns="http://rds.amazonaws.com/doc/2014-09-01/">
  <CreateDBParameterGroupResult>
    {{ db_parameter_group.to_xml() }}
  </CreateDBParameterGroupResult>
  <ResponseMetadata>
    <RequestId>7805c127-af22-11c3-96ac-6999cc5f7e72</RequestId>
  </ResponseMetadata>
</CreateDBParameterGroupResponse>"""

DESCRIBE_DB_PARAMETER_GROUPS_TEMPLATE = """<DescribeDBParameterGroupsResponse xmlns="http://rds.amazonaws.com/doc/2014-09-01/">
  <DescribeDBParameterGroupsResult>
    <DBParameterGroups>
    {%- for db_parameter_group in db_parameter_groups -%}
      {{ db_parameter_group.to_xml() }}
    {%- endfor -%}
    </DBParameterGroups>
  </DescribeDBParameterGroupsResult>
  <ResponseMetadata>
    <RequestId>b75d527a-b98c-11d3-f272-7cd6cce12cc5</RequestId>
  </ResponseMetadata>
</DescribeDBParameterGroupsResponse>"""

MODIFY_DB_PARAMETER_GROUP_TEMPLATE = """<ModifyDBParameterGroupResponse xmlns="http://rds.amazonaws.com/doc/2014-09-01/">
  <ModifyDBParameterGroupResult>
    <DBParameterGroupName>{{ db_parameter_group.name }}</DBParameterGroupName>
  </ModifyDBParameterGroupResult>
  <ResponseMetadata>
    <RequestId>12d7435e-bba0-11d3-fe11-33d33a9bb7e3</RequestId>
  </ResponseMetadata>
</ModifyDBParameterGroupResponse>"""

DELETE_DB_PARAMETER_GROUP_TEMPLATE = """<DeleteDBParameterGroupResponse xmlns="http://rds.amazonaws.com/doc/2014-09-01/">
  <ResponseMetadata>
    <RequestId>cad6c267-ba25-11d3-fe11-33d33a9bb7e3</RequestId>
  </ResponseMetadata>
</DeleteDBParameterGroupResponse>"""

DESCRIBE_DB_PARAMETERS_TEMPLATE = """<DescribeDBParametersResponse xmlns="http://rds.amazonaws.com/doc/2014-09-01/">
  <DescribeDBParametersResult>
    <Parameters>
      {%- for db_parameter_name, db_parameter in db_parameter_group.parameters.items() -%}
      <Parameter>
        {%- for parameter_name, parameter_value in db_parameter.items() -%}
        <{{ parameter_name }}>{{ parameter_value }}</{{ parameter_name }}>
        {%- endfor -%}
      </Parameter>
      {%- endfor -%}
    </Parameters>
  </DescribeDBParametersResult>
  <ResponseMetadata>
    <RequestId>8c40488f-b9ff-11d3-a15e-7ac49293f4fa</RequestId>
  </ResponseMetadata>
</DescribeDBParametersResponse>
"""

LIST_TAGS_FOR_RESOURCE_TEMPLATE = """<ListTagsForResourceResponse xmlns="http://rds.amazonaws.com/doc/2014-10-31/">
  <ListTagsForResourceResult>
    <TagList>
    {%- for tag in tags -%}
      <Tag>
        <Key>{{ tag['Key'] }}</Key>
        <Value>{{ tag['Value'] }}</Value>
      </Tag>
    {%- endfor -%}
    </TagList>
  </ListTagsForResourceResult>
  <ResponseMetadata>
    <RequestId>8c21ba39-a598-11e4-b688-194eaf8658fa</RequestId>
  </ResponseMetadata>
</ListTagsForResourceResponse>"""

ADD_TAGS_TO_RESOURCE_TEMPLATE = """<AddTagsToResourceResponse xmlns="http://rds.amazonaws.com/doc/2014-10-31/">
  <ResponseMetadata>
    <RequestId>b194d9ca-a664-11e4-b688-194eaf8658fa</RequestId>
  </ResponseMetadata>
</AddTagsToResourceResponse>"""

REMOVE_TAGS_FROM_RESOURCE_TEMPLATE = """<RemoveTagsFromResourceResponse xmlns="http://rds.amazonaws.com/doc/2014-10-31/">
  <ResponseMetadata>
    <RequestId>b194d9ca-a664-11e4-b688-194eaf8658fa</RequestId>
  </ResponseMetadata>
</RemoveTagsFromResourceResponse>"""

RESTORE_DB_INSTANCE_FROM_DB_SNAPSHOT_TEMPLATE = """<RestoreDBInstanceFromDBSnapshotResponse xmlns="http://rds.amazonaws.com/doc/2014-10-31/">
  <RestoreDBInstanceFromDBSnapshotResult>
    <DBInstance>
      <BackupRetentionPeriod>7</BackupRetentionPeriod>
      <MultiAZ>false</MultiAZ>
      <DBInstanceStatus>creating</DBInstanceStatus>
      <VpcSecurityGroups/>
      <DBInstanceIdentifier>{{ database.db_instance_identifier }}</DBInstanceIdentifier>
      <PreferredBackupWindow>08:14-08:44</PreferredBackupWindow>
      <PreferredMaintenanceWindow>fri:04:50-fri:05:20</PreferredMaintenanceWindow>
      <ReadReplicaDBInstanceIdentifiers/>
      <Engine>{{ database.engine }}</Engine>
      <PendingModifiedValues/>
      <LicenseModel>{{ database.license_model }}</LicenseModel>
      <EngineVersion>{{database.engine_version}}</EngineVersion>
      '''<DBParameterGroups>
        <DBParameterGroup>
          <ParameterApplyStatus>in-sync</ParameterApplyStatus>
          <DBParameterGroupName>default.mysql5.6</DBParameterGroupName>
        </DBParameterGroup>
      </DBParameterGroups>'''
      <OptionGroupMemberships>
        <OptionGroupMembership>
          <OptionGroupName>{{database.db_option_group_name}}</OptionGroupName>
          <Status>pending-apply</Status>
        </OptionGroupMembership>
      </OptionGroupMemberships>
      <PubliclyAccessible>{{database.publicly_accessible}}</PubliclyAccessible>
      '''<DBSecurityGroups>
        <DBSecurityGroup>
          <Status>active</Status>
          <DBSecurityGroupName>default</DBSecurityGroupName>
        </DBSecurityGroup>
      </DBSecurityGroups>'''
      <DBName>{{database.db_instance_identifier}}</DBName>
      <AutoMinorVersionUpgrade>true</AutoMinorVersionUpgrade>
      <AllocatedStorage>100</AllocatedStorage>
      <MasterUsername>myawsuser</MasterUsername>
      <DBInstanceClass>{{database.db_instance_class}}</DBInstanceClass>
    </DBInstance>
  </RestoreDBInstanceFromDBSnapshotResult>
  <ResponseMetadata>
    <RequestId>863fd73e-be2b-11d3-855b-576787000e19</RequestId>
  </ResponseMetadata>
</RestoreDBInstanceFromDBSnapshotResponse>
"""
