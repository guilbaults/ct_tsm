 CREATE TABLE `SOFT_RM_DELAYED` (
  `id` varbinary(64) NOT NULL,
  `rm_time` int(10) unsigned DEFAULT NULL,
  `lhsm_uuid` varbinary(36) DEFAULT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8;

delimiter #
create trigger SOFT_RM_INSERT after insert on SOFT_RM
for each row
begin
  insert into SOFT_RM_DELAYED (id, rm_time, lhsm_uuid) values (new.id, new.rm_time, new.lhsm_uuid);
end#

delimiter ;
